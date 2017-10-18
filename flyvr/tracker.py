from numpy import sign

from time import perf_counter
from math import pi, tan, radians
from threading import Lock

from flyvr.service import Service

class TrackThread(Service):
    def __init__(self,
                 camThread, # handle of the camera thread
                 cncThread, # handle of the CNC control thread
                 loopTime=5e-3, # target loop update rate
                 fc = 1.2, # crossover frequency, Hz
                 minAbsPos = 8.5e-3, # m
                 maxAbsVel = 0.75, # m/s
                 maxAbsAcc = 0.25, # m/s^2
                 ):

        # Store thread handles
        self.camThread = camThread
        self.cncThread = cncThread

        # Create lock for handling manual control
        self.manualCtrlLock = Lock()
        self.manualControl = None

        # Store settings
        self.minAbsPos = minAbsPos
        self.maxAbsVel = maxAbsVel
        self.maxAbsAcc = maxAbsAcc

        # Compute derived parameters of control loop
        wc = 2*pi*fc
        self.a = wc

        # Initialize the control loop
        self.prevVelX = 0
        self.prevVelY = 0

        # Set the starting time
        self.lastTime = perf_counter()
                 
        # call constructor from parent        
        super().__init__(minTime=loopTime, maxTime=loopTime)

    # overriding method from parent...
    def loopBody(self):
        # read current time
        thisTime = perf_counter()
        dt = thisTime - self.lastTime

        # get latest camera data
        flyData = self.camThread.flyData

        # store fly position information            
        if flyData is not None:
            flyX = flyData.flyX
            flyY = flyData.flyY
            flyPresent = flyData.flyPresent
        else:
            flyX = 0
            flyY = 0
            flyPresent = False

        # get manual control information
        manualControl = self.manualControl

        if manualControl:
            velX = manualControl.velX
            velY = manualControl.velY
        else:
            # update velocities from fly position
            if flyPresent:
                velX = self.updateFromFlyPos(flyX)
                velY = self.updateFromFlyPos(flyY)
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

    # control update based on fly position
    # PI controller approximated by bilinear transform of
    # continuous time transfer function
    def updateFromFlyPos(self, cam):
        if abs(cam) <= self.minAbsPos:
            return 0
        else:
            return self.a*cam

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

    @property
    def manualControl(self):
        with self.manualCtrlLock:
            return self._manualControl

    @manualControl.setter
    def manualControl(self, val):
        with self.manualCtrlLock:
              self._manualControl = val
    
class ManualControl:
    def __init__(self, velX, velY):
        self.velX = velX
        self.velY = velY
