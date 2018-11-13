from time import time, sleep
from math import pi
from threading import Lock, Event
from numpy import sign

from flyvr.service import Service
from flyvr.cnc import cnc_home, CncThread

class TrackThread(Service):
    def __init__(self,
                 camThread=None, # handle of the camera thread
                 loopTime=5e-3, # target loop update rate
                 loop_gain_a = 10.0, # loop gain, in m/s per m offset from center (original value 2*pi*1.2)
                 minAbsPos = 0.5e-3, # deadzone half-width in meters (original value 8.5mm)
                 maxAbsVel = 0.75, # m/s
                 maxAbsAcc = 1, # m/s^2 (original value 0.25 m/s^2)

                 v_max_ctrl = 0.04, # m/s
                 k_pctrl = 2*pi,

                 center_pos_x = 0.348625,
                 center_pos_y = 0.332775,
                 manual_pos_tol= 1e-3
                 ):

        # Store thread handles
        self.camThreadLock = Lock()
        self._camThread = camThread

        self.cncThreadLock = Lock()
        self._cncThread = None

        self.cnc_shouldinitialize = Event()
        self.is_init = False

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
        self.manual_pos_tol = manual_pos_tol

        # Initialize the control loop
        self.prevVelX = 0
        self.prevVelY = 0

        # Set the starting time
        self.lastTime = time()

        # Set manual jog velocity
        self.manual_jog_vel = 0.02
                 
        # call constructor from parent        
        super().__init__(minTime=loopTime, maxTime=loopTime, iter_warn=False)

    @property
    def camThread(self):
        with self.camThreadLock:
            return self._camThread

    @camThread.setter
    def camThread(self, value):
        with self.camThreadLock:
            self._camThread = value

    @property
    def cncThread(self):
        with self.cncThreadLock:
            return self._cncThread

    @cncThread.setter
    def cncThread(self, value):
        with self.cncThreadLock:
            self._cncThread = value

    # overriding method from parent...
    def loopBody(self):
        if self.cnc_shouldinitialize.is_set():
            if self.cncThread is not None:
                print('Closing previous cncThread...')
                self.cncThread.stop()

            print('Homing CNC...')
            cnc_home()
            print('Done homing CNC.')

            print('Creating a new cncThread...')
            self.cncThread = CncThread()
            self.cncThread.start()

            print('Starting to move to center...')
            self.start_moving_to_center()

            self.is_init = True
            self.cnc_shouldinitialize.clear()
        if self.cncThread is None:
            print('Creating a cncThread since none exists.')
            self.cncThread = CncThread()
            self.cncThread.start()

        #print('cnc: ', self.cncThread)
        #print('cam: ', self.camThread)
        # read current time
        thisTime = time()
        dt = thisTime - self.lastTime

        # get latest camera data
        try:
            flyData = self.camThread.flyData
        except:
            flyData = None

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

        velX = 0
        velY = 0

        if manualPosition is not None:
            if self.is_close_to_pos(self.manualPosition.posX, self.manualPosition.posY):
                print('Got to specified manual position.')
                self.manualPosition = None
            else:
                cncStatus = self.cncThread.status
                try:
                    velX = self.k_pctrl*(manualPosition.posX - cncStatus.posX)
                    velY = self.k_pctrl*(manualPosition.posY - cncStatus.posY)
                except:
                    print('Problem setting velocity for manual position control.')

                if abs(velX) > self.v_max_pctrl:
                    velX = float(sign(velX)*self.v_max_pctrl)
                if abs(velY) > self.v_max_pctrl:
                    velY = float(sign(velY)*self.v_max_pctrl)
        elif manualVelocity is not None:
            velX = manualVelocity.velX
            velY = manualVelocity.velY
        elif self.trackingEnabled and flyPresent:
            # update velocities from fly position
            velX = self.updateFromFlyPos(flyX)
            velY = self.updateFromFlyPos(flyY)

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

    # For gui control
    def manual_move_up(self):
        self.manualVelocity = ManualVelocity(velX=0, velY= +self.manual_jog_vel)
    def manual_move_down(self):
        self.manualVelocity = ManualVelocity(velX=0, velY= -self.manual_jog_vel)
    def manual_move_right(self):
        self.manualVelocity = ManualVelocity(velX= +self.manual_jog_vel, velY=0)
    def manual_move_left(self):
        self.manualVelocity = ManualVelocity(velX= -self.manual_jog_vel, velY=0)

    def manual_stop(self):
        self.manualVelocity = None

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

    def mark_center(self):
        cnc_status = self.cncThread.status
        self.center_pos_x = cnc_status.posX
        self.center_pos_y = cnc_status.posY
        self.cnc_init = True

    def startLogging(self, path):
        self.cncThread.startLogging(path)

    def stopLogging(self):
        self.cncThread.stopLogging()

    def start_moving_to_center(self):
        self.start_moving_to_pos(x=self.center_pos_x, y=self.center_pos_y)

    def start_moving_to_pos(self, x, y):
        self.manualPosition = ManualPosition(x, y)

    def is_close_to_pos(self, x, y):
        try:
            cncStatus = self.cncThread.status
            return ((abs(x - cncStatus.posX) <= self.manual_pos_tol) and
                    (abs(y - cncStatus.posY) <= self.manual_pos_tol))
        except:
            print('Bad CNC status in is_close_to_pos, defaulting to False...')
            return False

    def is_close_to_center(self):
        return self.is_close_to_pos(self.center_pos_x, self.center_pos_y)

    def cleanup(self):
        try:
            self.cncThread.stop()
        except:
            print('Could not shut down cncThread for some reason.')

class ManualVelocity:
    def __init__(self, velX, velY):
        self.velX = velX
        self.velY = velY

class ManualPosition:
    def __init__(self, posX, posY):
        self.posX = posX
        self.posY = posY