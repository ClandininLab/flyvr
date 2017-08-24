from time import perf_counter
from math import pi, tan, radians

from service import Service

class TrackThread(Service):
    def __init__(self,
                 camThread, # handle of the camera thread
                 cncThread, # handle of the CNC control thread
                 loopTime=10e-3, # target loop update rate
                 fc = 0.1, # crossover frequency, Hz
                 phase_margin = 60, # phase margin, degrees
                 maxAbsVel = 0.75, # m/s
                 maxAbsAcc = 0.25, # m/s^2
                 minPosX = -1, # m
                 maxPosX = +1, # m
                 minPosY = -1, # m
                 maxPosY = +1 # m
                 ):

        # Store thread handles
        self.camThread = camThread
        self.cncThread = cncThread

        # Store settings
        self.maxAbsVel = maxAbsVel
        self.maxAbsAcc = maxAbsAcc
        self.minPosX = minPosX
        self.maxPosX = maxPosX
        self.minPosY = minPosY
        self.maxPosY = maxPosY

        # Compute derived parameters of control loop
        wc = 2*pi*fc
        self.a = wc*tan(radians(phase_margin))
        self.b = wc**2

        # Initialize the control loop
        self.prevVelX = 0
        self.prevVelY = 0
        self.prevCamX = 0
        self.prevCamY = 0

        # Set the starting time
        self.lastTime = perf_counter()
                 
        # call constructor from parent        
        super().__init__(minTime=loopTime, maxTime=loopTime)

    # overriding method from parent...
    def loopBody(self):
        # read current time
        thisTime = perf_counter()
        dt = thisTime - self.lastTime
        
        # get latest CNC position
        cncStatus = self.cncThread.status
        if cncStatus is not None:
            cncX = cncStatus.posX
            cncY = cncStatus.posY
        else:
            return
        
        # get latest raw fly position
        flyData = self.camThread.flyData
        if flyData is not None:
            camX = flyData.flyX
            camY = flyData.flyY
            flyPresent = flyData.flyPresent
        else:
            return

        if flyPresent:
            # update velocities from fly position
            velX = self.updateFromFlyPos(camX, self.prevCamX, self.prevVelX, dt)
            velY = self.updateFromFlyPos(camY, self.prevCamY, self.prevVelY, dt)
            
            # update velocities from CNC position
            velX = self.updateFromCncPos(cncX, velX, self.minPosX, self.maxPosX)
            velY = self.updateFromCncPos(cncY, velY, self.minPosY, self.maxPosY)
        else:
            velX = 0
            velY = 0

        # update velocities based on velocity limits
        velX = self.updateFromMaxVel(velX)
        velY = self.updateFromMaxVel(velY)

        # update velocities based on acceleration limits
        velX = self.updateFromMaxAcc(velX, self.prevVelX, dt)
        velY = self.updateFromMaxAcc(velY, self.prevVelY, dt)

        # update CNC velocity
        self.cncThread.setVel(velX, velY)

        # save history variables
        self.lastTime = thisTime
        self.prevVelX = velX
        self.prevVelY = velY
        self.prevCamX = camX
        self.prevCamY = camY

    # control update based on fly position
    def updateFromFlyPos(self, cam, prevCam, prevVel, dt):
        return prevVel + (self.b*dt/2 + self.a)*cam + (self.b*dt/2 - self.a)*prevCam

    # control update based on CNC position
    def updateFromCncPos(self, cnc, vel, minPos, maxPos):
        if (cnc <= minPos and vel <= 0) or (cnc >= maxPos and vel >= 0):
            return 0
        else:
            return vel

    # control update based on maximum velocity
    def updateFromMaxVel(self, vel):
        if vel <= -self.maxAbsVel:
            return -self.maxAbsVel
        elif vel >= self.maxAbsVel:
            return self.maxAbsVel
        else:
            return vel

    # control update based on maximum acceleration
    def updateFromMaxAcc(self, vel, prevVel, dt):
        # compute acceleration
        acc = TrackThread.calcAcc(vel, prevVel, dt)

        # limit acceleration
        if acc <= -self.maxAbsAcc:
            return prevVel - self.maxAbsAcc*dt
        elif acc >= self.maxAbsAcc:
            return prevVel + self.maxAbsAcc*dt
        else:
            return vel

    # calculate acceleration, handling divide-by-zero cases
    @staticmethod
    def calcAcc(vel, prevVel, dt):
        dv = vel-prevVel
        if dt != 0:
            return dv/dt
        else:
            if dv < 0:
                return -float('inf')
            elif dv > 0:
                return +float('inf')
            else:
                return 0
  
