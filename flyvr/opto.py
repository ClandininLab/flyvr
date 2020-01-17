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
        self.foraging_distance_min = 0.03 #from center
        self.foraging_distance_max = 0.2
        self.path_distance_min = 0.01 #min walk distance

        #self.foragingNextFood_t_min =
        #self.foragingNextFood_t_max =
        #self.foragingNextFood_d_min =
        #self.foragingNextFood_d_min =

        self.foodspots = []
        self.food_rad = 0.005  #radius of foodspot
        self.fly_movement_threshold = 0.5e-3
        self.time_of_last_food = None
        self.time_since_last_food = None
        self.time_since_last_food_min = 30 #in sec
        self.long_time_since_food = True
        self.shouldCreateFood = False
        self.led_status = 'off'
        self.fly_in_food = False
        self.far_from_food = False
        self.min_dist_from_food = 0.2 #in m
        self.distance_since_last_food = 0
        self.list_prev_y = [0]
        self.list_prev_x = [0]
        self.min_distance_removes_food = .01 #20cm  #dancing radius allowed  #testing .01 (1cm)

        # Set food creation parameters false
        self.far_from_food = False
        self.distance_correct = False  #for center
        self.path_distance_correct = False  #total path
        self.long_time_since_food = False
        self.fly_moving = False
        self.max_foodspots = 90
        self.more_food = False #if false then reached max foodspots
        self.time_override = False  ##if true will override time off restriction if the fly is 3cm away from foodspot


        self.dist_from_center = None
        self.total_distance = 0
        self.trial_start_t = None
        self.closest_food = None
        self.camX = None
        self.camY = None

        self.flyInQuadrant1 = False
        self.flyInQuadrant2 = False
        self.flyInQuadrant3 = False
        self.flyInQuadrant4 = False

        self.shouldCheckFoodDistance = True
        self.shouldCheckFlyDistanceFromCenter = True
        self.shouldCheckTimeSinceFood = True
        self.shouldCheckFlyIsMoving = True
        self.shouldCheckTotalPathDistance = False
        self.shouldCheckNumberFoodspots = False
        self.shouldAllowDancing = False



        self.time_in_out_change = None
        self.food_boundary_hysteresis = 0.1 #0.01 #time
        self.food_distance_hysteresis = 0.005 #distance

        #parameters for food pulse times
        self.set_off_time = False
        self.set_on_time = False
        self.min_off_time = 9.0
        self.max_on_time = 1.0 #1s
        self.off_time_track = 0  #0
        self.on_time_track = 0
        self.on_time_correct = False
        self.off_time_correct = False
        self.current_off_time = 0
        self.current_on_time = 0
        self.full_light_on = True  #to designate that the light will stay on for full on time even if fly leaves foodspot



        # call constructor from parent        
        super().__init__(maxTime=maxTime, minTime=minTime)

    # overriding method from parent...
    def loopBody(self):
        if self.trial_start_t is None:
            self.off()

        ### Get Fly Position ###

        if self.camThread is not None and self.camThread.fly is not None:
            self.camX = self.camThread.fly.centerX
            self.camY = self.camThread.fly.centerY
        else:
            self.camX = None
            self.camY = None

        if self.cncThread is not None and self.cncThread.status is not None:
            cncX = self.cncThread.status.posX
            cncY = self.cncThread.status.posY
        else:
            cncX = None
            cncY = None

        if self.camX is not None and cncX is not None:
            self.flyX = self.camX + cncX
            self.flyY = self.camY + cncY
        else:
            self.flyX = None
            self.flyY = None

        ### Calculate parameters based on fly position ###

        if self.flyX is not None and self.flyY is not None and self.trial_start_t is not None:
            # calculate distance from center
            x_dist = np.abs(self.flyX) - np.abs(self.trackThread.center_pos_x)
            y_dist = np.abs(self.flyY) - np.abs(self.trackThread.center_pos_y)
            self.dist_from_center = np.sqrt(x_dist*x_dist + y_dist*y_dist)

            #Calculate total length of fly travel path
            immediate_distance = np.sqrt((abs(x_dist)-abs(self.list_prev_x[-1]))**2 + (abs(y_dist)-abs(self.list_prev_y[-1]))**2)
            self.list_prev_x.append(x_dist) #update list of checked values
            self.list_prev_y.append(y_dist)
            self.total_distance += immediate_distance  # running total
            self.distance_since_last_food += immediate_distance  # this resets with every foodspot

            if self.foraging:
                # define food spot if all requirements are met
                self.checkFoodCreation()

                # if self.shouldAllowDancing == True:
                #     self.dance()

                if self.shouldCreateFood:
                    self.defineFoodSpot()  #this records the foodspot so the led will turn on
                    self.shouldCreateFood = False

                # turn on LED if fly is in food spot
                for foodspot in self.foodspots:
                    if foodspot['x'] - self.food_rad <= self.flyX <= foodspot['x'] + self.food_rad and \
                       foodspot['y'] - self.food_rad <= self.flyY <= foodspot['y'] + self.food_rad:
                        self.time_of_last_food = time()
                        self.distance_since_last_food = 0 #reset distance when get to food
                        self.fly_in_food = True
                        #print("fly in foodspot food")
                        continue
                    else:
                        self.fly_in_food = False



                if self.time_in_out_change is None or time() - self.time_in_out_change >= self.food_boundary_hysteresis:
                    if self.fly_in_food:
                        if self.led_status == 'off': #fly has just entered food or led on time has elapsed
                            self.time_in_out_change = time()
                            if self.set_off_time == False: #if don't care about off time then turn on
                                self.on()
                            if self.set_off_time == True: #turn the light on only if off time has passed
                                if (time() - self.off_time_track) > self.min_off_time:
                                    self.on()
                        if self.led_status == 'on':
                            if self.set_on_time == True: #turn the light off if it has been on too long
                                if (time() - self.on_time_track) > self.max_on_time:
                                    self.off()
                    else:
                        # if self.led_status == 'on':
                        #     self.time_in_out_change= time()
                        #     self.off()

                        if self.led_status == 'on':
                            if self.full_light_on == False: #turn it off regularly
                                self.time_in_out_change = time()
                                self.off()
                            #if condition to keep light on for entire on time is selected
                            # even if fly has left foodspot then wait until time is up to turn off
                            if self.full_light_on == True:
                                if self.set_on_time == True:  # turn the light off if it has been on too long
                                    if (time() - self.on_time_track) > self.max_on_time:
                                        #do I need to reset time_in_out_change here?
                                        self.time_in_out_change = time()
                                        self.off()
# def determineQuadrant(self):
#         if self.flyX > self.trackThread.center_pos_x and self.flyY > self.trackThread.center_pos_y:
#             self.flyInQuadrant1 = True
#         if self.flyX > self.trackThread.center_pos_x and self.flyY < self.trackThread.center_pos_y:
#             sel



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

        ### Check - walked far enough ###
        if self.distance_since_last_food is not None:
            if self.distance_since_last_food > self.path_distance_min:
                self.path_distance_correct = True
            else:
                self.path_distance_correct = False

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

        #adding criteria that foodspot not be at the same location or very close to another foodspot
        if self.closest_food is not None:
            if self.closest_food <= self.food_distance_hysteresis: #if food is too close (could also have it be "or < self.food_radius)"
                self.shouldCreateFood = False  #added to prevent too many foodspots if don't have a distance requirement
                return

        if self.shouldCheckFoodDistance:
            if not self.far_from_food:
                self.shouldCreateFood = False
                return

        if self.shouldCheckFlyDistanceFromCenter:
            if not self.distance_correct:
                self.shouldCreateFood = False
                return

        if self.shouldCheckTotalPathDistance:
            if not self.path_distance_correct:
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

        if self.shouldCheckNumberFoodspots:
            ### see if number of foodspots is less than max ##
            if len(self.foodspots) < self.max_foodspots:
                self.more_food = True
            else:
                self.more_food = False
            if not self.more_food:
                self.shouldCreateFood = False
                return
    def determineQuadrant(self):
        if self.flyX > self.trackThread.center_pos_x and self.flyY > self.trackThread.center_pos_y:
            self.flyInQuadrant1 = True
        if self.flyX > self.trackThread.center_pos_x and self.flyY < self.trackThread.center_pos_y:
            sel
        if self.set_off_time and not self.time_override:  #if should check off time to see if another spot should be made
            if (time() - self.off_time_track) <= self.min_off_time: #if min time hasn't passed
                self.shouldCreateFood = False
                self.off_time_correct = False
                return

        if self.set_off_time and self.time_override: #if both set off time and time override are selected
            if self.distance_since_last_food <= .003: #if it is close to food then don't turn on food, otherwise do
                print("too close to food-> no override", self.closest_food)
                self.shouldCreateFood = False
                return

        if self.set_on_time: #if the on time has not elapsed then another foodspot should not be made either
                # (this is important if there is nothing else except timing selected)
            if (time() - self.on_time_track) <= self.max_on_time: #if time hasn't passed
                self.shouldCreateFood = False
                self.on_time_correct = False
                return




        self.shouldCreateFood = True

    def defineFoodSpot(self):
        print("foodspot defined. closest food = ", self.closest_food)
        self.foodspots.append({'x': self.flyX, 'y': self.flyY})
        self.logFood(self.flyX, self.flyY)

    # def dance(self):
    #     if self.closest_food is not None and self.closest_food > self.min_distance_removes_food:
    #         self.foodspots = []  #removes all previous foodspots if it gets far away from one
    #         self.logFoodRemoval()
    #     if self.closest_food is not None and self.closest_food <= self.min_distance_removes_food:
    #         #prevent more food from being created
    #         self.shouldCreateFood = False

    def determineQuadrant(self):
        if self.flyX > self.trackThread.center_pos_x and self.flyY > self.trackThread.center_pos_y:
            self.flyInQuadrant1 = True
        if self.flyX > self.trackThread.center_pos_x and self.flyY < self.trackThread.center_pos_y:
            self.flyInQuadrant2 = True
        if self.flyX < self.trackThread.center_pos_x and self.flyY < self.trackThread.center_pos_y:
            self.flyInQuadrant3 = True
        if self.flyX < self.trackThread.center_pos_x and self.flyY > self.trackThread.center_pos_y:
            self.flyInQuadrant4 = True



    def on(self):
        print('TURNED ON')
        self.led_status = 'on'
        self.logLED(self.led_status)
        self.write(self.ON_COMMAND)
        self.on_time_track = time()

    def off(self):
        #print('TURNED OFF')
        self.led_status = 'off'
        self.logLED(self.led_status)
        self.write(self.OFF_COMMAND)
        self.off_time_track = time()

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


    ##added this to try to get to save opto AS
    def getLogState(self):
        with self.logLock:
            return self.logState, self.logFile

            # # log status
            # ##added this to try to get to save opto AS
            # logState, logFile = self.getLogState()
            # if logState:
            #     logStr = (str(time()) + ',' +
            #               str(status.posX) + ',' +
            #               str(status.posY) + '\n')
            #     logFile.write(logStr)

    def logLED(self, led_status):
        with self.logLock:
            if self.logFile is not None:
                print("log file not none in led status logging")
                self.logFile.write('{}, {}, {}\n'.format('led', time(), led_status))
                self.logFile.flush()

    def logFood(self, x, y):
        #print("log food called")
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}, {}, {}\n'.format('food', time(), x, y))
                self.logFile.flush()
                print("foodspot logged")

    def logFoodRemoval(self):
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}\n'.format('food-removed', time()))
                self.logFile.flush()

    def logFoodRevisitNoFood(self, x, y):
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}, {}, {}\n'.format('food-revisited but not given food', time(), x, y))
                self.logFile.flush()

    def startLogging(self, logFile):
        with self.logLock:
            self.logState = True
            if self.logFile is not None:
                print("logFile is not none")
                self.logFile.close()
                print("log file closed")

            self.logFile = open(logFile, 'w')
            print("logFile opened")
            #uncommented below to try to get opto to save AS
            self.logFile.write('time, LED Status\n')

    def stopLogging(self):
        with self.logLock:

            self.logState = False

            if self.logFile is not None:
                self.logFile.close()
                print("log file closed--stop logging called")
                self.logFile = None