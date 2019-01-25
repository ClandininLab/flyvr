import serial, platform
import os.path

from math import pi
import numpy as np
from time import sleep, time
from threading import Lock, Thread
import serial.tools.list_ports

from flyvr.service import Service
from flyvr.tracker import TrackThread
from flyvr.trial import TrialThread
from flyvr.cnc import CncThread
from flyvr.camera import CamThread

from flyvr.util import serial_number_to_comport

class OptoThread(Service):
    ON_COMMAND = 0xbe
    OFF_COMMAND = 0xef

    def __init__(self, cncThread=None, camThread=None, trackThread=None, minTime=5e-3, maxTime=12e-3):
        # Serial interface to opto arduino
        com = None
        if com is None:
            if platform.system() == 'Linux':
                com = serial_number_to_comport('557323235303519180B1')
            else:
                raise Exception('Opto not supported on this platform.')

        # set up serial connection
        self.ser = serial.Serial(port=com, baudrate=9600)
        sleep(2)

        # Setup locks
        self.pulseLock = Lock()
        self.logLock = Lock()
        self.logFile = None
        self.logState = False

        # Store thread handles
        self.camThread = camThread
        self.cncThread = cncThread
        self.trackThread = trackThread

        # Set foraging parameters
        self.foraging = False
        self.foraging_time_min = 2
        self.foraging_time_override = 3*(60)
        self.foraging_distance_min = 0.05
        self.foraging_distance_max = 0.2

        #self.foragingNextFood_t_min =
        #self.foragingNextFood_t_max =
        #self.foragingNextFood_d_min =
        #self.foragingNextFood_d_min =

        self.foodspots = []
        self.food_rad = 5e-3
        self.fly_movement_threshold = 0.5e-3
        self.time_of_last_food = None
        self.time_since_last_food = None
        self.time_since_last_food_min = 30 #in sec
        self.long_time_since_food = True
        self.shouldCreateFood = False
        self.led_status = 'off'
        self.fly_in_food = False
        self.far_from_food = False
        self.min_dist_from_food = 0.010 #in m

        # Set food creation parameters false
        self.far_from_food = False
        self.distance_correct = False
        self.long_time_since_food = False
        self.fly_moving = False

        self.dist_from_center = None
        self.trial_start_t = None
        self.closest_food = None
        self.camX = None
        self.camY = None

        self.shouldCheckFoodDistance = True
        self.shouldCheckFlyDistanceFromCenter = True
        self.shouldCheckTimeSinceFood = True
        self.shouldCheckFlyIsMoving = True

        # call constructor from parent        
        super().__init__(maxTime=maxTime, minTime=minTime)

    # overriding method from parent...
    def loopBody(self):
        ### Get Fly Position ###

        if self.camThread is not None and self.camThread.flyData is not None:
            camX = self.camThread.flyData.flyX
            camY = self.camThread.flyData.flyY
            flyPresent = self.camThread.flyData.flyPresent
        else:
            camX = None
            camY = None
            flyPresent = False

        if self.cncThread is not None and self.cncThread.status is not None:
            cncX = self.cncThread.status.posX
            cncY = self.cncThread.status.posY
        else:
            cncX = None
            cncY = None

        if camX is not None and cncX is not None and flyPresent is True:
            self.flyX = camX + cncX
            self.flyY = camY + cncY
        else:
            self.flyX = None
            self.flyY = None

        ### Calculate parameters based on fly position ###

        if self.flyX is not None and self.flyY is not None and self.trial_start_t is not None:
            # calculate distance from center
            x_dist = np.abs(self.flyX) - np.abs(self.trackThread.center_pos_x)
            y_dist = np.abs(self.flyY) - np.abs(self.trackThread.center_pos_y)
            self.dist_from_center = np.sqrt(x_dist*x_dist + y_dist*y_dist)

            if self.foraging:
                # define food spot if all requirements are met
                self.checkFoodCreation()
                if self.shouldCreateFood:
                    self.defineFoodSpot()
                    self.shouldCreateFood = False

                # turn on LED if fly is in food spot
                for foodspot in self.foodspots:
                    if foodspot['x'] - self.food_rad <= self.flyX <= foodspot['x'] + self.food_rad and \
                       foodspot['y'] - self.food_rad <= self.flyY <= foodspot['y'] + self.food_rad:
                        self.time_of_last_food = time()
                        self.fly_in_food = True
                        continue
                    else:
                        self.fly_in_food = False

                if self.fly_in_food:
                    if self.led_status == 'off':
                        self.on()
                else:
                    if self.led_status == 'on':
                        self.off()

    def checkFoodCreation(self):

        ### Check - make sure food isn't too close to other food ###
        if len(self.foodspots) > 0:
            self.food_distances = []
            for food in self.foodspots:
                x_dist = self.flyX - food['x']
                y_dist = self.flyY - food['y']
                self.food_distances.append(np.sqrt(x_dist * x_dist + y_dist * y_dist))

            self.closest_food = np.min(self.food_distances)

            if self.closest_food >= self.min_dist_from_food:
                self.far_from_food = True
            else:
                self.far_from_food = False
        else:
            self.far_from_food = True

        ### Check - far from center ###
        if self.dist_from_center is not None:
            if self.dist_from_center >= self.foraging_distance_min:
                self.distance_correct = True
            else:
                self.distance_correct = False

        ### Check - make sure the fly hasn't recently passed through a spot ###
        if self.time_of_last_food is not None:
            self.time_since_last_food = time() - self.time_of_last_food
            if self.time_since_last_food > self.time_since_last_food_min:
                self.long_time_since_food = True
            else:
                self.long_time_since_food = False
        else:
            self.long_time_since_food = True

        ### Check - make sure fly is moving ###
        if self.camX is not None:
            if abs(self.camX) > self.fly_movement_threshold or \
               abs(self.camY) > self.fly_movement_threshold:
               self.fly_moving = True
            else:
                self.fly_moving = False

        ### ARE ALL CONDITIONS MET? ###

        if self.shouldCheckFoodDistance:
            if not self.far_from_food:
                self.shouldCreateFood = False
                return

        if self.shouldCheckFlyDistanceFromCenter:
            if not self.distance_correct:
                self.shouldCreateFood = False
                return

        if self.shouldCheckTimeSinceFood:
            if not self.long_time_since_food:
                self.shouldCreateFood = False
                return

        if self.shouldCheckFlyIsMoving:
            if not self.fly_moving:
                self.shouldCreateFood = False
                return

        self.shouldCreateFood = True

    def defineFoodSpot(self):
        self.foodspots.append({'x': self.flyX, 'y': self.flyY})
        self.logFood(self.flyX, self.flyY)

    def on(self):
        self.led_status = 'on'
        self.logLED(self.led_status)
        self.write(self.ON_COMMAND)

    def off(self):
        self.led_status = 'off'
        self.logLED(self.led_status)
        self.write(self.OFF_COMMAND)

    def write(self, cmd):
        self.ser.write(bytearray([cmd]))

    def pulse(self, on_duration=0.1, off_duration=9.9):
        def target():
            while True:
                self.on()
                sleep(on_duration)
                self.off()
                sleep(off_duration)

        Thread(target=target).start()

    def logLED(self, led_status):
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}, {}\n'.format('led', time(), led_status))
                self.logFile.flush()

    def logFood(self, x, y):
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}, {}, {}\n'.format('food', time(), x, y))
                self.logFile.flush()

    def startLogging(self, logFile):
        with self.logLock:

            self.logState = True

            if self.logFile is not None:
                self.logFile.close()

            self.logFile = open(logFile, 'w')
            #self.logFile.write('time, LED Status\n')

    def stopLogging(self):
        with self.logLock:

            self.logState = False

            if self.logFile is not None:
                self.logFile.close()
                self.logFile = None