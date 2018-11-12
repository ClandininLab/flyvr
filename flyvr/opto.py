import serial, platform
import os.path

from math import pi
import numpy as np
from time import sleep, time
from threading import Lock, Thread
import serial.tools.list_ports

from flyvr.service import Service
from flyvr.tracker import TrackThread
from flyvr.cnc import CncThread
from flyvr.camera import CamThread

from flyvr.util import serial_number_to_comport

class OptoThread(Service):
    ON_COMMAND = 0xbe
    OFF_COMMAND = 0xef

    def __init__(self, cncThread=None, camThread=None, trackThread=None, TrialThread=None):
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
        self.trackThread = TrackThread
        self.trialThread = trialThread

        # Set foraging parameters
        self.foraging = False
        self.foraging_time_min = 2
        self.foraging_time_override = 3*(60)
        self.foraging_distance_min = 0.05
        self.foraging_distance_max = 0.2

        self.foragingNextFood_t_min = 
        self.foragingNextFood_t_max = 
        self.foragingNextFood_d_min = 
        self.foragingNextFood_d_min = 

        self.foodspots = []
        self.food_rad = 5e-3
        self.fly_movement_threshold = 0.5e-3
        self.time_since_last_food = None
        self.time_since_last_food_min = 30 #sec
        self.long_time_since_food = True
        self.shouldCreateFood = False

        # call constructor from parent        
        super().__init__()

    # overriding method from parent...
    def loopBody(self):
        if self.camThread is not None:

            # get latest camera position
            flyData = self.camThread.flyData
            if flyData is not None:
                camX = flyData.flyX
                camY = flyData.flyY
                flyPresent = flyData.flyPresent
            else:
                camX = 0
                camY = 0
                flyPresent = False

            # get latest cnc position
            if self.cncThread is not None:
                if self.cncThread.status is not None:
                    cncX = self.cncThread.status.posX
                    cncY = self.cncThread.status.posY
                else:
                    cncX = 0
                    cncY = 0

                # find fly position
                self.flyX = camX + cncX
                self.flyY = camY + cncY

                # calculate distance from center
                x_dist = np.abs(self.flyX - self.trackThread.center_pos_x)
                y_dist = np.abs(self.flyY - self.trackThread.center_pos_y)
                self.dist_from_center = np.sqrt(x_dist*x_dist + y_dist*y_dist)
        
                if self.foraging:
                    # define food spot if all requirements are met
                    checkFoodCreation()
                    if self.shouldCreateFood:
                        defineFoodSpot()
                        self.shouldCreateFood = False


                    # turn on LED if fly is in food spot
                    for foodspot in foodspots:
                        if foodspot.x - self.food_rad <= self.flyX <= foodspot.x - self.food_rad and \
                           foodspot.y - self.food_rad <= self.flyY <= foodspot.y - self.food_rad:
                           #turn on LED
                           time_since_last_food = time()








            # temporary opto logic
            #if flyX > self.trackThread.center_pos_x:
            #    self.on()
            #else:
            #    self.off()

    def checkFoodCreation(self):
        # time is large or distance correct: (consider removing time override?)
        if ((time() - self.trial.trial_start_t > self.foraging_time_override) or \
            self.foraging_distance_max > self.dist_from_center > self.foraging_distance_min):
            self.distance_correct = True

        # make sure fly is moving
        if abs(camX) > fly_movement_threshold or \
           abs(camY) > fly_movement_threshold:
           self.fly_moving = True

        # make sure the fly hasn't recently passed through a spot
        if (time() - time_since_last_food > self.time_since_last_food_min):
            self.long_time_since_food = True

        if self.distance_correct and self.fly_moving and self.long_time_since_food:
            self.shouldCreateFood = True

    def defineFoodSpot(self):
        foodspots.append({x: self.flyX, y: self.flyY})

    def on(self):
        self.log('on')
        self.write(self.ON_COMMAND)

    def off(self):
        self.log('off')
        self.write(self.OFF_COMMAND)

    def write(self, cmd):
        self.ser.write(bytearray([cmd]))

    def pulse(self, duration=1):
        def target():
            with self.pulse_lock:
                self.on()
                sleep(duration)
                self.off()

        Thread(target=target).start()

    def log(self, led_status):
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}\n'.format(time(), led_status))
                self.logFile.flush()

    def startLogging(self, logFile):
        with self.logLock:

            self.logState = True

            if self.logFile is not None:
                self.logFile.close()

            self.logFile = open(logFile, 'w')
            self.logFile.write('time, LED Status\n')

    def stopLogging(self):
        with self.logLock:

            self.logState = False

            if self.logFile is not None:
                self.logFile.close()