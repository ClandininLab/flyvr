import time
import numpy as np

from math import sin, pi, ceil, sqrt, degrees, acos
from threading import Thread, Lock

from cnc import CNC
from camera import Camera

cnc = CNC()
cncLock = Lock()
cncCmdX = 0
cncCmdY = 0
cncDone = False

def cncThread():
    done = False

    iterCount = 0
    startTime = time.time()
    
    while not done:
        # update iteration count
        iterCount += 1
        
        # read/write
        cncLock.acquire()
        done = cncDone
        cmdX = cncCmdX
        cmdY = cncCmdY
        cncLock.release()
        
        # set velocity
        cnc.setVel(cmdX, cmdY)

    loopTime = (time.time()-startTime)/iterCount
    print('CNC Loop Time: ' + str(loopTime*1e3) + ' (ms)') 

cam = Camera(thresh=80)
camLock = Lock()
camPosX = 0
camPosY = 0
camFlyPresent = False
camDone = False

def camThread():
    global camPosX
    global camPosY
    global camFlyPresent
    
    done = False

    iterCount = 0
    startTime = time.time()
    
    while not done:
        # update iteration count
        iterCount += 1
        
        # process image
        posX, posY, flyPresent = cam.getFlyPos()

        # read/write
        camLock.acquire()
        done = camDone
        camPosX = posX
        camPosY = posY
        camFlyPresent = flyPresent
        camLock.release()

    loopTime = (time.time()-startTime)/iterCount
    print('Camera Loop Time: ' + str(loopTime*1e3) + ' (ms)') 

def measPhase(yvec, vvec, tvec):
    T = tvec[-1] - tvec[0]
    yvec0 = 1.0/T * np.trapz(yvec, tvec)
    vvec0 = 1.0/T * np.trapz(vvec, tvec)
    a = float(np.trapz((yvec-yvec0)*(vvec-vvec0), tvec))
    b = float(np.trapz((yvec-yvec0)**2, tvec))
    c = float(np.trapz((vvec-vvec0)**2, tvec))
    return acos(a/sqrt(b*c))

def measAmpl(yvec, tvec):
    T = tvec[-1] - tvec[0]
    yvec0 = 1.0/T * np.trapz(yvec, tvec)
    return float(sqrt(2.0/T * np.trapz((yvec-yvec0)**2, tvec)))

def main():
    global cncCmdX
    global cncCmdY
    global cncDone
    global camDone
    
    # testing parameters    
    ampl0 = 0.005
    minFreq = 0.1
    maxFreq = 25
    nFreq = 50
    tstop = 10

    # reset parameters
    centerX = 0.401
    centerY = 0.405
    settleDelay = 2
    threadLaunchDelay = 1

    # limits of velocity and acceleration
    maxAbsVel = 0.75 # m/s
    maxAbsAcc = 2.0 # m/s^2

    # general frequency list
    freq_list = np.logspace(np.log10(minFreq), np.log10(maxFreq), nFreq)
    freq_list = [float(freq) for freq in freq_list]
    freq_list = freq_list[-10:-3]

    # axis list
    axisList = ['X']

    for axis in axisList:
        # create new file
        fname = 'Stepper Freq Resp ' + axis + '.txt'
        with open(fname, 'w') as f:
            pass

        # iterate over frequencies
        for freq in freq_list:
            print(freq)

            # compute exact length of the trial to ensure an integer number of trials
            tstop_round = ceil(tstop*freq)/freq

            # create empty lists to hold results
            v = []
            y = []
            x = []
            tvec = []

            # move to reset position and settle
            cnc.goToPos(centerX, centerY)
            time.sleep(settleDelay)

            # initialize CNC variables
            cncCmdX = 0
            cncCmdY = 0
            cncDone = False

            # initialize camera variables
            camDone = False

            # launch CNC thread
            cncHandle = Thread(target=cncThread)
            cncHandle.start()

            # launch camera thread
            camHandle = Thread(target=camThread)
            camHandle.start()

            # wait for threads to launch
            time.sleep(threadLaunchDelay)
            
            # oscillate at the specified frequency
            startTime = time.time()            
            while True:
                t = time.time() - startTime

                # determine if the trial is over
                if t > tstop_round:
                    break

                # add time to time vector
                tvec = tvec + [t]

                # compute amplitude
                ampl = ampl0*freq
                ampl = min(ampl, maxAbsVel)
                ampl = min(ampl, maxAbsAcc/(2*pi*freq))

                # compute velocity
                vel = ampl*sin(2*pi*freq*t)
                v = v + [vel]
                                                
                if axis == 'X':
                    cmdX = vel
                    cmdY = 0
                elif axis == 'Y':
                    cmdX = 0
                    cmdY = vel
                else:
                    raise Exception('Invalid axis')

                # update velocity
                cncLock.acquire()
                cncCmdX = cmdX
                cncCmdY = cmdY
                cncLock.release()

                # get the fly position                
                camLock.acquire()
                posX = camPosX
                posY = camPosY
                flyPresent = camFlyPresent
                camLock.release()

                # end program if fly is lost
                if not flyPresent:
                    cncLock.acquire()
                    cncCmdX = 0
                    cncCmdY = 0
                    cncLock.release()
                    time.sleep(1)
                    raise Exception('Fly lost.')

                # record the measured position
                x = x + [posX]
                y = y + [posY]

                # delay before next iteration
                time.sleep(5e-3)

            # stop CNC thread
            cncLock.acquire()
            cncCmdX = 0
            cncCmdY = 0
            cncDone = True
            cncLock.release()
            cncHandle.join()

            # stop camera thread
            camLock.acquire()
            camDone = True
            camLock.release()
            camHandle.join()

            # turn measurements into numpy arrays
            vvec = np.array(v)
            xvec = np.array(x)
            yvec = np.array(y)
            tvec = np.array(tvec)

            # measure parameters of system
            in_ampl = measAmpl(vvec, tvec)
            out_ampl_x = measAmpl(xvec, tvec)
            out_ampl_y = measAmpl(yvec, tvec)
            phase_x = degrees(measPhase(xvec, vvec, tvec))
            phase_y = degrees(measPhase(yvec, vvec, tvec))

            # write out measurements to file
            nums = [freq, in_ampl, out_ampl_x, out_ampl_y, phase_x, phase_y]
            nums = [str(num) for num in nums]
            with open(fname, 'a') as f:
                f.write(', '.join(nums) + '\n')

    f.close()
                       
if __name__=='__main__':
    main()
