from time import time, sleep
from math import pi
from threading import Lock
from numpy import sign

from flyvr.service import Service

class TrackThread(Service):
    def __init__(self,
                 camThread, # handle of the camera thread
                 cncThread, # handle of the CNC control thread
                 loopTime=5e-3, # target loop update rate
                 loop_gain_a = 10.0, # loop gain, in m/s per m offset from center (original value 2*pi*1.2)
                 minAbsPos = 0.5e-3, # deadzone half-width in meters (original value 8.5mm)
                 maxAbsVel = 0.75, # m/s
                 maxAbsAcc = 1, # m/s^2 (original value 0.25 m/s^2)

                 v_max_ctrl = 0.04, # m/s
                 k_pctrl = 2*pi,

                 center_pos_x = 0.348625,
                 center_pos_y = 0.332775
                 ):

        # Store thread handles
        self.camThread = camThread
        self.cncThread = cncThread

        # Create lock for handling manual velocity
        self.manualVelLock = Lock()
        self._manualVelocity = None

        # Create lock for handling manual position
        self.manualPosLock = Lock()
        self._manualPosition = None

        # Variable sets whether track is enabled
        self.trackingEnableLock = Lock()
        self._trackingEnabled = False

        # Store settings
        self.minAbsPos = minAbsPos
        self.maxAbsVel = maxAbsVel
        self.maxAbsAcc = maxAbsAcc
        self.k_pctrl = k_pctrl
        self.v_max_pctrl = v_max_ctrl

        # Compute derived parameters of control loop
        self.a = loop_gain_a

        # Set the center pos
        self.center_pos_x = center_pos_x
        self.center_pos_y = center_pos_y

        # Initialize the control loop
        self.prevVelX = 0
        self.prevVelY = 0

        # Set the starting time
        self.lastTime = time()
                 
        # call constructor from parent        
        super().__init__(minTime=loopTime, maxTime=loopTime)

    # overriding method from parent...
    def loopBody(self):
        # read current time
        thisTime = time()
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
        manualVelocity = self.manualVelocity
        manualPosition = self.manualPosition

        if manualPosition is not None:
            cncStatus = self.cncThread.status
            velX = self.k_pctrl*(manualPosition.posX - cncStatus.posX)
            velY = self.k_pctrl*(manualPosition.posY - cncStatus.posY)
            if abs(velX) > self.v_max_pctrl:
                velX = float(sign(velX)*self.v_max_pctrl)
            if abs(velY) > self.v_max_pctrl:
                velY = float(sign(velY)*self.v_max_pctrl)
        elif manualVelocity is not None:
            velX = manualVelocity.velX
            velY = manualVelocity.velY
        elif self.trackingEnabled:
            # update velocities from fly position
            if flyPresent:
                velX = self.updateFromFlyPos(flyX)
                velY = self.updateFromFlyPos(flyY)
            else:
                velX = 0
                velY = 0
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
    def manualVelocity(self):
        with self.manualVelLock:
            return self._manualVelocity

    @manualVelocity.setter
    def manualVelocity(self, val):
        with self.manualVelLock:
              self._manualVelocity = val

    @property
    def manualPosition(self):
        with self.manualPosLock:
            return self._manualPosition

    @manualPosition.setter
    def manualPosition(self, val):
        with self.manualPosLock:
              self._manualPosition = val

    @property
    def trackingEnabled(self):
        with self.trackingEnableLock:
            return self._trackingEnabled

    @trackingEnabled.setter
    def trackingEnabled(self, value):
        with self.trackingEnableLock:
            self._trackingEnabled = value

    def startTracking(self):
        self.trackingEnabled = True

    def stopTracking(self):
        self.trackingEnabled = False

    def set_center_pos(self, posX, posY):
        # TODO add locking
        self.center_pos_x = posX
        self.center_pos_y = posY

    def move_to_center(self):
        # TODO add locking
        self.move_to_pos(x=self.center_pos_x, y=self.center_pos_y)

    def move_to_pos(self, x, y, tol=1e-3):
        self.manualPosition = ManualPosition(x, y)

        def isError():
            cncStatus = self.cncThread.status
            if cncStatus is None:
                return True
            else:
                return (abs(x-cncStatus.posX) > tol) or (abs(y-cncStatus.posY) > tol)

        while isError():
            pass

        self.manualPosition = None

class ManualVelocity:
    def __init__(self, velX, velY):
        self.velX = velX
        self.velY = velY

class ManualPosition:
    def __init__(self, posX, posY):
        self.posX = posX
        self.posY = posY