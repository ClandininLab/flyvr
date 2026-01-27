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
from random import choice

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

        # general variables to set
        self.camX = None
        self.camY = None
        self.led_status = 'off'
        self.trial_start_t = None

        # set foodspot parameters and variables
        self.foodspots = []  # stores the x,y location of foodspots
        self.food_rad = 0.005  # radius of foodspot
        self.fly_movement_threshold = 0.5e-3  # amount the camx or camy must be greater than to say the fly is moving
        self.food_boundary_hysteresis = 0.1  # 0.01 #time
        self.food_distance_hysteresis = 0.005  # distance

        # Set foraging parameters
        self.foraging = False  #if foraging button selected in GUI this will change to true
        self.foraging_distance_min = 0.03 #distane from center requirement in meters
        self.path_distance_min = 0.01 #min walk distance from a foodspot to make more food
        self.min_dist_from_food = 0.05  # in meters. min geo distance the fly must walk to get a new foodspot
        self.distance_since_last_food = 0  #needs to start at 0 resets each time gets food, this is path distance
        self.list_prev_y = [0]  #involved in tracking the total distance the fly walks
        self.list_prev_x = [0]  #involved in tracking the total distance the fly walks
        self.max_foodspots = 90  # to control the number of foodspots (set high, but this won't turn on unless selected)
        self.time_since_last_food_min = 30  # in sec minimum amount of time required to elapse before food made
        self.total_distance = 0  #collects running total of distance walked
        self.distance_away_required = .03  # this is the distance away from a foodspot a fly needs to walk for the override of the off time

        #set foodspot creation parameters
        self.shouldCreateFood = False #if true then makes a foodspot
        self.fly_in_food = False  #to determine if the light should come on
        self.time_of_last_food = None #stores absolute time (time()) of when previous foodspot was given
        self.time_since_last_food = None  #subtract current time from time_of_last_food (relative rather than absolute)
        self.long_time_since_food = False  #if elapsed time has been greater than the minimum
        self.far_from_food = False #state to store if fly is far enough away from previous foodspot
        self.distance_correct = False  #true if fly is far enough away from the center
        self.path_distance_correct = False  #true if fly has walked far enough since the previous food (path style)
        self.fly_moving = False #true if fly is moving
        self.more_food = True #if false then reached max foodspots or max duration
        self.time_override = False  ##if true will override time off restriction if the fly is self.distance_away_required away from foodspot
        self.dist_from_center = None #straight line distance from center
        self.closest_food = None #should store the distance to the closest foodspot (of all foodspots)
        self.shouldCheckFoodDistance = True
        self.shouldCheckFlyDistanceFromCenter = True
        self.shouldCheckTimeSinceFood = True
        self.shouldCheckFlyIsMoving = True
        self.shouldCheckTotalPathDistance = False
        self.shouldCheckNumberFoodspots = False
        self.shouldCheckMaxFoodTime = False # change to True manually until GUI is changed
        self.shouldRandomizeOffTime = False #manually change to true until GUI is changed
        self.shouldRandomizePathDistance = False
        self.shouldRandomizeFoodDistance = False

        # self.override_allowed = False #changes true when fly is 3cm from foodspot ---no longer used
        self.distance_away_reached = False  #use this to make sure the fly moves 3cm from the last foodspot before giving food again
        #make sure this condition is only checked if the off time is short
        self.allowfoodspotreturns = False ## if True this should allow flies to get new light if they are in a foodspot and time has not elapsed
        #self.time_in_out_change = None #rests to current time every time the light turns off to keep track of off time (7.19.22 replacing this with off_time_track)
        print(f'foodspots allowed: {self.allowfoodspotreturns}')

        #parameters for light pulse times
        self.set_off_time = False
        self.set_on_time = False
        self.min_off_time = 10.0
        self.max_on_time = 1.0 #1s
        self.off_time_track = 0  #0
        self.on_time_track = 0
        self.on_time_correct = False
        self.off_time_correct = False
        self.current_off_time = 0
        self.current_on_time = 0
        self.full_light_on = True  #to designate that the light will stay on for full on time even if fly leaves foodspot #I changed this to true verify right in gui 20240821
        self.fly_in_previous_foodspot = False
        self.max_food_time = 120 # seconds of elapsed experiment time 

        #to override max_off time with a random selection, specified below (20240824 - also need to add this to gui)
        if self.shouldRandomizeOffTime == True:
            self.min_off_time = choice([10, 20, 40, 60]) #not currently set in GUI to specify these
            print(f'min off time by randomize chosen = {self.min_off_time}')
        if self.shouldRandomizeFoodDistance == True:
            self.shouldCheckFoodDistance = True
            self.min_dist_from_food = choice([.05, .15]) #, 40, 60]) #not currently set in GUI to specify these
            print(f'min euc distance from food by randomize chosen = {self.min_dist_from_food}')
        if self.shouldRandomizePathDistance == True:
            self.path_distance_min = choice([.05, .15]) #, 40, 60]) #not currently set in GUI to specify these
            #self.distance_away_required = choice([5, 15]) #distance_away_required is for off_time override not for distance
            self.shouldCheckTotalPathDistance = True
            print(f'min path distance from food by randomize chosen = {self.path_distance_min}')

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

            # #Calculate total length of fly travel path (previous version
            # immediate_distance = np.sqrt((abs(x_dist)-abs(self.list_prev_x[-1]))**2 + (abs(y_dist)-abs(self.list_prev_y[-1]))**2)
            # self.list_prev_x.append(x_dist) #update list of checked values
            # self.list_prev_y.append(y_dist)
            # self.total_distance += immediate_distance  # running total
            # self.distance_since_last_food += immediate_distance  # this resets with every foodspot

            #1.26.26 new version with some euc movement required (choose based on distance from center)
            #need it not to update for every twitch the fly does. require distance of some value before adding to path
            #Calculate total length of fly travel path
            immediate_distance = np.sqrt((abs(x_dist)-abs(self.list_prev_x[-1]))**2 + (abs(y_dist)-abs(self.list_prev_y[-1]))**2)
            if immediate_distance > .005: #requires moves half a cm before updating
                self.list_prev_x.append(x_dist) #update list of checked values
                self.list_prev_y.append(y_dist)
                self.total_distance += immediate_distance  # running total
                self.distance_since_last_food += immediate_distance  # this resets with every foodspot


            if self.foraging:
                # define food spot if all requirements are met
                self.checkFoodCreation()

                #if find that food should be created, record a foodspot and change shouldcreatefood state back to false
                if self.shouldCreateFood and self.more_food == True: #more_food will be false if the duration of food allowed is reached or max foodspots reached
                    self.defineFoodSpot()  #this records the foodspot x,y coordinates in foodspots and logs it in txt file
                    self.on() #this may break things, but I think not. 
                    self.shouldCreateFood = False

                # changes fly_in_food state to true if fly is in foodspot by checking x,y positions with the food_radius as a buffer
                #also resets the time_of_last_food and the distance_since_last_food
                
                for foodspot in self.foodspots:
                    if foodspot['x'] - self.food_rad <= self.flyX <= foodspot['x'] + self.food_rad and \
                       foodspot['y'] - self.food_rad <= self.flyY <= foodspot['y'] + self.food_rad:
                        self.time_of_last_food = time()
                        self.distance_since_last_food = 0 #reset distance when get to food
                        self.fly_in_food = True
                        #print("fly in foodspot!")
                        #print(foodspot)
                        # #maybe I should have a condition that if it is not the most recent foodspot no other things matter except override and off time
                        # if self.allowfoodspotreturns == True and foodspot != self.foodspots[-1]:
                        #     if  self.fly_in_food == True: #if it isn't the last foodspot and the fly is in it
                        #         self.fly_in_previous_foodspot = True
                        #     else:
                        #         self.fly_in_previous_foodspot = False
                        continue

                    else:
                        self.fly_in_food = False
                        # self.fly_in_previous_foodspot = False  ##can't put this here because it will check the last foodspot last

                #set up checking for previous foodspots
                if self.allowfoodspotreturns == True:
                    for foodspot in self.foodspots[:-1]:  #since this is looking for previous foodspots, ignore the most recent one
                        if foodspot['x'] - self.food_rad <= self.flyX <= foodspot['x'] + self.food_rad and \
                           foodspot['y'] - self.food_rad <= self.flyY <= foodspot['y'] + self.food_rad:
                            self.time_of_last_food = time()
                            self.distance_since_last_food = 0 #reset distance when get to food
                            self.fly_in_food = True
                            self.fly_in_previous_foodspot = True
                            print(f"fly returned to foodspot! {foodspot}")
                            continue
                        else:
                            self.fly_in_previous_foodspot = False
                if self.allowfoodspotreturns is False and self.set_off_time == False: #if off_time is on it doesn't really matter if the fly walks over a foodspot again 
                    if self.fly_in_previous_foodspot == True: 
                        #don't make more food or turn on light!
                        self.off #this should keep light off, I think
                        self.shouldCreateFood = False #this should be unnecessary
                        print('no light - fly in previous food and allow foodspot returns is false')

                ## This controls if the light will TURN ON and TURN OFF and is dependent on if the fly is in the food
                    #the first line checks to make sure the light doesn't flicker on and off due to tracking issues by having a time hysteresis if the light had recently turned opn
                #self.time_in_out_change resets every time the light turns off to keep track of off time
                #if self.time_in_out_change is None or time() - self.time_in_out_change >= self.food_boundary_hysteresis: #boundary_hysteresis is in time
                if time() - self.off_time_track >= self.food_boundary_hysteresis: #boundary_hysteresis is in time

                    if self.fly_in_food:
                        if self.led_status == 'off': #the light is off when the fly is in food if the fly has just entered food or led on time has elapsed
                            if self.set_off_time == False and self.allowfoodspotreturns == True: #if don't care about off time elapsing then turn on
                                self.on()
                            elif self.set_off_time == False and self.allowfoodspotreturns == False: #if don't care about off time elapsing then turn on
                                #need to make sure it's the first time
                                if self.shouldCreateFood == True:
                                    self.on()
                            elif self.set_off_time == True and self.time_override == False:  #turn the light on only if off time has passed and it doesn't meet override criteria
                                if (time() - self.off_time_track) > self.min_off_time: #if off time passage is greater than min off time then turn on
                                    self.on()
                            #if time override is true then allow foodspot to turn on even if time has not elapsed (check to make sure this doesn't always overrride distance)
                            elif self.set_off_time == True and self.time_override == True and self.distance_away_reached == True: #turn the light on
                                self.on()
                                print('on because override allowed')
                            #also need a condition so it will turn on if the time has elapsed even if teh override is true (could probably combo this into previous one, but I'll keep it separate)
                            elif self.set_off_time == True and self.time_override == True and self.distance_away_reached == False:
                                if (time() - self.off_time_track) > self.min_off_time: #if off time passage is greater than min off time then turn on
                                    self.on()
                                    print('on because of THIS condition at line 224')
                            else:
                                print('no light on, state not specified--distance away reached = ', self.distance_away_reached)


                        elif self.led_status == 'on':
                            if self.set_on_time == True: #turn the light off if it has been on too long
                                if (time() - self.on_time_track) > self.max_on_time:
                                    #self.time_in_out_change = time()  #6.5.20 adding this here because it doesn't make sense to only have it sometimes when the light turns off?
                                    self.off()
                    #this will only be true if allow previous foodspot returns is selected
                    elif self.fly_in_previous_foodspot:  
                        print('fly in previous foodspot')
                        self.on()
                    #    if self.led_status == 'off':
                    #         if self.set_off_time == False: #if don't care about off time elapsing then turn on
                    #             self.on()
                    #         elif self.set_off_time == True:  #turn the light on only if off time has passed and it doesn't meet override criteria
                    #             if (time() - self.off_time_track) > self.min_off_time: #if off time passage is greater than min off time then turn on
                    #                 self.on()

                    #if fly_in_food is False
                    elif self.fly_in_food is False:  #previously just else
                        #turn off the light if it was on (unless full_light_on selected then keep it on until light on time is up)
                        if self.led_status == 'on':
                            if self.full_light_on == False: #turn it off regularly (regular = light turns off when fly leaves foodspot)
                                #self.time_in_out_change = time()
                                self.off()
                            #if condition to keep light on for entire on time is selected
                            # even if fly has left foodspot then wait until time is up to turn off
                            elif self.full_light_on == True:  #if keep light on for on time selected
                                if self.set_on_time == True:  # turn the light off if it has been on too long
                                    if (time() - self.on_time_track) > self.max_on_time:
                                        #self.time_in_out_change = time()
                                        self.off()




    def checkFoodCreation(self):

        ### Check - make sure food isn't too close to other food ###
        ##only need to do this if the close food checkbox is checked, right? check that nothing will break otherwise?
        #if self.shouldCheckFoodDistance:  #new change 2022 commenting this requirement out so hysteresis still works, needs to have closest food measurement to work
        if len(self.foodspots) > 0: #and shouldCheckFoodDistance = True?
            self.food_distances = []  #this needs to be reset each time because I am just using it to store for a calculation of closest distance compared to all curent foodspots
            for food in self.foodspots: #look at each foodspot and find the euc distance between current position and each spot and store in a list
                x_dist = self.flyX - food['x']
                y_dist = self.flyY - food['y']
                self.food_distances.append(np.sqrt(x_dist * x_dist + y_dist * y_dist))
            self.closest_food = np.min(self.food_distances) #find the distance to the closest foodspot
            if self.shouldCheckFoodDistance: #adding these for food distance since removed from top, may not be necessary
                if self.closest_food >= self.min_dist_from_food:
                    self.far_from_food = True
                    print(f'fly is far from food {self.far_from_food}. min distance = {self.min_dist_from_food}')
                else:
                    self.far_from_food = False
        else: #if there is no foodspot then the fly is automatically far_from_food
            if self.shouldCheckFoodDistance: #adding these for food distance since removed from top, may not be necessary
                self.far_from_food = True

        ### Check - far from center ###
        if self.dist_from_center is not None:
            if self.dist_from_center >= self.foraging_distance_min:
                self.distance_correct = True
            else:
                self.distance_correct = False

        ### Check - walked far enough as path length ###
        if self.distance_since_last_food is not None: #distance since last food stores each xy change and resets when fly returns to foodspot or gets a new one
            if self.distance_since_last_food > self.path_distance_min:  ##would be good to read out distance_since_last_food in the GUI to make sure it works well
                self.path_distance_correct = True
            else:
                self.path_distance_correct = False

        
        ### Check - walked away from foodspot ###
        if self.distance_since_last_food is not None and self.time_override == True:
            if self.distance_since_last_food > self.distance_away_required:  # distance away required set to 3cm (to allow a fly to move away and gt a new foodspot within off-time)
                self.distance_away_reached = True
                #print("distance away reached achieved")
            else:
                self.distance_away_reached = False

        ### Check - make sure the fly hasn't recently passed through a spot ###
        if self.time_of_last_food is not None:
            self.time_since_last_food = time() - self.time_of_last_food
            if self.time_since_last_food > self.time_since_last_food_min:
                self.long_time_since_food = True
            else:
                self.long_time_since_food = False
        else:
            self.long_time_since_food = True  #since the fly wouldnt have had food yet

        ### Check - make sure fly is moving ###
        if self.camX is not None:
            if abs(self.camX) > self.fly_movement_threshold or \
               abs(self.camY) > self.fly_movement_threshold:
               self.fly_moving = True
            else:
                self.fly_moving = False


        #adding criteria that foodspot not be at the same location or very close to another foodspot (must be food_distance_hysteresis away even if no other restrictions)
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
                self.shouldCreateFood = False
                return
            
        ## add max time for foodspots here (i.e. 2 minutes of foodspots allowed (at other parameters and then no more))
        #this is new! test! 20240821
        if self.shouldCheckMaxFoodTime:
            if self.trial_start_t and (time() - self.trial_start_t)  >= self.max_food_time: ##self.trial_start_t is set to time() at the start of the trial 
                self.shouldCreateFood = False   
                self.more_food = False
                print(f"no more food because allowed duration for food has elapsed. Duration = {self.max_food_time} s ")
        
        #if the on time has not elapsed then another foodspot should not be made either
        #not sure why there are still a couple foodspots if the fly moves while light remains on...7.22.22
        if self.set_on_time and (time() - self.on_time_track) <= self.max_on_time: 
            self.shouldCreateFood = False
            self.on_time_correct = False
            print("no new food because on time not over")
            return

        #food should not be made if off time has not elapsed and time override is false
        if self.time_override == False and self.set_off_time and (time() - self.off_time_track) <= self.min_off_time: #if the on time has not elapsed then another foodspot should not be made either
            self.shouldCreateFood = False
            self.on_time_correct = False
            return

        ##if time_override is true then check if distance requirement has been met (added 7.19.22)
        if self.time_override == True and self.set_off_time and self.distance_away_reached == False: 
            self.shouldCreateFood = False
            return

        


        self.shouldCreateFood = True
        print('foodspot creation = True')



    def defineFoodSpot(self):
        self.foodspots.append({'x': self.flyX, 'y': self.flyY})
        self.logFood(self.flyX, self.flyY)
        print(f"new food location: {self.foodspots[-1]}")
        if self.closest_food is not None:
            print("foodspot defined. closest food = ", self.closest_food)  
            print(f'path distance to previous foodspot = {self.distance_since_last_food}')
        else:
            print("foodspot defined")




    def on(self):
        print('TURNED ON (in opto)')
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
        #self.time_in_out_change = time()

    def write(self, cmd):
        self.ser.write(bytearray([cmd]))

    def pulse(self, on_duration=5, off_duration=5):
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

    # def logFoodRevisitNoFood(self, x, y):
    #     with self.logLock:
    #         if self.logFile is not None:
    #             self.logFile.write('{}, {}, {}, {}\n'.format('food-revisited but not given food', time(), x, y))
    #             self.logFile.flush()

    def startLogging(self, logFile):
        with self.logLock:
            self.logState = True
            if self.logFile is not None:
                print("logFile is not none")
                self.logFile.close()
                print("log file closed")

            self.logFile = open(logFile, 'w')
            print("logFile opened")
            self.logFile.write('time, LED Status\n')

    def stopLogging(self):
        with self.logLock:

            self.logState = False

            if self.logFile is not None:
                self.logFile.close()
                print("log file closed--stop logging called")
                self.logFile = None
