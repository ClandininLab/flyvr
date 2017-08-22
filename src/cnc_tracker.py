import time
import cv2

from math import pi, tan, radians, ceil

from cnc import CncThread
from camera import CamThread, ImageType

def nothing(x):
    pass

def clamp(v, minV, maxV):
    if v < minV:
        return minV
    elif v > maxV:
        return maxV
    else:
        return v
    
def main():    
    # Parameters of the control loop
    fc = 0.4 # crossover frequency, Hz
    phase_margin = 60 # phase margin, degrees

    # limits of velocity and acceleration
    maxAbsVel = 0.30 # m/s
    maxAbsAcc = 0.25 # m/s^2

    # boundaries of the arena
    minPosX = -1 #0.15
    maxPosX = +1 #0.65
    minPosY = -1 #0.15
    maxPosY = +1 #0.65

    # settings for UI
    tPer = ceil(1e3/24)
    typeDir = {0: ImageType.RAW, 1: ImageType.GRAY, 2: ImageType.THRESH}

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 150, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)    

    # Open file for logging
    timestr = time.strftime('%Y%m%d-%H%M%S')
    f = open(timestr + '.csv', 'w')

    # Open connection to CNC rig
    cnc = CncThread()
    cnc.start()

    # Open connection to camera
    cam = CamThread()
    cam.start()

    # Wait for CNC and camera data to appear
    while cnc.status is None or cam.status is None:
        time.sleep(100e-3)

    # Make sure CNC is stopped and get initial position reading
    cncStatus = cnc.status
    cncX, cncY = cncStatus.posX, cncStatus.posY

    # Compute derived parameters of control loop
    wc = 2*pi*fc
    a = wc*tan(radians(phase_margin))
    b = wc**2
    minVel = -maxAbsVel
    maxVel = +maxAbsVel
    
    # Initialize the control loop
    prevVelX = 0
    prevVelY = 0
    prevCamX = 0
    prevCamY = 0

    lastTime = time.time()

    # control update based on fly position
    def updateFromFlyPos(cam, prevCam, prevVel, dt):
        return prevVel + (b*dt/2 + a)*cam + (b*dt/2 - a)*prevCam

    # control update based on CNC position
    def updateFromCncPos(cnc, vel, minPos, maxPos):
        if (cnc <= minPos and vel <= 0) or (cnc >= maxPos and vel >= 0):
            return 0
        else:
            return vel

    # control update based on maximum velocity
    def updateFromMaxVel(vel):
        if vel <= -maxAbsVel:
            return -maxAbsVel
        elif vel >= maxAbsVel:
            return maxAbsVel
        else:
            return vel

    # control update based on maximum acceleration
    def updateFromMaxAcc(vel, prevVel, dt):
        # compute acceleration
        dv = vel-prevVel
        if dt != 0:
            acc = dv/dt
        else:
            if dv < 0:
                acc = -float('inf')
            elif dv > 0:
                acc = +float('inf')
            else:
                acc = 0

        # limit acceleration
        if acc <= -maxAbsAcc:
            return prevVel - maxAbsAcc*dt
        elif acc >= maxAbsAcc:
            return prevVel + maxAbsAcc*dt
        else:
            return vel
    
    while True:
        # adjust threshold
        threshTrack = cv2.getTrackbarPos('threshold', 'image')
        cam.threshold = threshTrack + 1

        # adjust image type
        typeTrack = cv2.getTrackbarPos('imageType', 'image')
        cam.imageType = typeDir[typeTrack]
        
        # get raw fly position
        camData = cam.status
        camX = camData.flyX
        camY = camData.flyY
        flyPresent = camData.flyPresent

        # draw the image if status available
        if flyPresent:
            cv2.drawContours(camData.outFrame, [camData.flyContour], 0, (0, 255, 0), 2)
        # show the image
        cv2.imshow('image', camData.outFrame)

        # read current time
        thisTime = time.time()
        dt = thisTime - lastTime

        if flyPresent:
            # update velocities from fly position
            velX = updateFromFlyPos(camX, prevCamX, prevVelX, dt)
            velY = updateFromFlyPos(camY, prevCamY, prevVelY, dt)
            
            # update velocities from CNC position
            velX = updateFromCncPos(cncX, velX, minPosX, maxPosX)
            velY = updateFromCncPos(cncY, velY, minPosY, maxPosY)
        else:
            velX = 0
            velY = 0

        # update velocities based on velocity limits
        velX = updateFromMaxVel(velX)
        velY = updateFromMaxVel(velY)

        # update velocities based on acceleration limits
        velX = updateFromMaxAcc(velX, prevVelX, dt)
        velY = updateFromMaxAcc(velY, prevVelY, dt)

        # update CNC velocity
        cnc.setVel(velX, velY)

        # log current position
        cncStatus = cnc.status
        cncX, cncY = cncStatus.posX, cncStatus.posY

        # write log file
        f.write(str(thisTime) + ', ')
        f.write(str(flyPresent) + ', ')
        f.write(str(camX) + ', ' + str(camY) + ', ')
        f.write(str(cncX) + ', ' + str(cncY) + '\n')

        # save some variables from this iteration
        lastTime = thisTime
        prevVelX = velX
        prevVelY = velY
        prevCamX = camX
        prevCamY = camY

        # get user input, wait until next frame
        key = cv2.waitKey(tPer)
        if key==27:
            break

    # close UI window
    cv2.destroyAllWindows()

    # stop processing frames
    cam.stop()

    # stop communicating with CNC
    cnc.stop()

    # print out CNC thread information
    print('CNC interval (ms): ', cnc.avePeriod*1e3)

    # print out camera thread information
    print('Camera FPS: ', 1/cam.avePeriod)
        
if __name__ == '__main__':
    main()
