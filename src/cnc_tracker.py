import time
from math import pi, tan, radians

from cnc import CncThread
from camera import CamThread

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
    minPosX = 0.15
    maxPosX = 0.65
    minPosY = 0.15
    maxPosY = 0.65

    # Open file for logging
    timestr = time.strftime('%Y%m%d-%H%M%S')
    f = open(timestr + '.csv', 'w')

    # Open connection to CNC rig and camera
    cnc = CncThread()
    cam = CamThread()

    # Make sure CNC is stopped and get initial position reading
    cnc.setVel(0, 0)
    cncX = cnc.status.posX
    cncY = cnc.status.posY

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
        acc = (vel-prevVel)/dt

        # limit acceleration
        if acc <= -maxAbsAcc:
            return prevVel - maxAbsAcc*dt
        elif acc >= maxAbsAcc:
            return prevVel + maxAbsAcc*dt
        else:
            return vel
    
    while(True):        
        # get raw fly position
        camX, camY, flyPresent = cam.getFlyPos()

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

        # update CNC velocity and log position
        cnc.setVel(velX, velY)
        cncX = cnc.status.posX
        cncY = cnc.status.posY

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

        # display debugging image
        if not cam.displayFrame():
            break
        
if __name__ == '__main__':
    main()
