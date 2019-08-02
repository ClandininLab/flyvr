import cv2
import os
import platform
import os.path
import itertools

from time import strftime, time, sleep

from flyvr.service import Service
from threading import Lock
from flyvr.tracker import TrackThread, ManualVelocity

class TrialThread(Service):
    def __init__(self, cam, cnc, dispenser, stim, opto, tracker, ui, flyplot,
                 loopTime=10e-3, fly_lost_timeout=2, fly_detected_timeout=2):

        self.trial_count = itertools.count(1)
        self.state = 'started'
        self.prev_state = 'started'

        self.cam = cam
        self.cnc = cnc
        self.dispenser = dispenser
        self.stim = stim
        self.opto = opto
        self.ui = ui
        self.tracker = tracker
        self.flyplot = flyplot

        self.timer_start = None
        self.trial_start_t = None
        self.trial_end_t = None

        self.fly_lost_timeout = fly_lost_timeout
        self.fly_detected_timeout = fly_detected_timeout

        # set up access to the thread-ending signal
        self.manualLock = Lock()
        self._manualCmd = None

        self.trialDirLock = Lock()
        self._trial_dir = None

        # create folder for data
        if platform.system() == 'Windows':
            topdir = r'F:\FlyVR'
        elif platform.system() == 'Linux':
            topdir = '/mnt/fly-data/FlyVR'
        else:
            raise Exception('Invalid platform.')

        # create top-level experiment directory
        self.exp = 'exp-'+strftime('%Y%m%d-%H%M%S')
        self.exp_dir = os.path.join(topdir, self.exp)
        os.makedirs(self.exp_dir)

        # start logging to dispenser
        if self.dispenser is not None:
            self.dispenser.start_logging(self.exp_dir)

        # call constructor from parent
        super().__init__(minTime=loopTime, maxTime=loopTime, iter_warn=False)

    @property
    def trial_dir(self):
        with self.trialDirLock:
            return self._trial_dir

    def _start_trial(self):
        self.trial_start_t = time()
        self.tracker.startTracking()
        self.trial_num = next(self.trial_count)
        print('Started trial ' + str(self.trial_num))
        folder = 'trial-' + str(self.trial_num) + '-' + strftime('%Y%m%d-%H%M%S')
        _trial_dir = os.path.join(self.exp_dir, folder)
        self._trial_dir = _trial_dir
        os.makedirs(_trial_dir)

        self.tracker.startLogging(os.path.join(_trial_dir, 'cnc.txt'))
        self.cam.startLogging(os.path.join(_trial_dir, 'cam.txt'),os.path.join(_trial_dir, 'cam_compr.mkv'))

        if self.opto is not None:
            self.opto.startLogging(os.path.join(_trial_dir, 'opto.txt'))
            self.opto.trial_start_t = self.trial_start_t


            # added resets tp start pf trial to try to fix foodspot issue and reset time when trial starts
            # reset opto
            self.opto.trial_start_t = self.trial_start_t
            self.opto.stopLogging()
            self.opto.foodspots = []
            self.opto.closest_food = None
            self.opto.fly_in_food = False

            self.opto.dist_from_center = None
            self.opto.total_distance = 0
            self.opto.distance_since_last_food = 0
            self.opto.closest_food = None
            self.opto.far_from_food = False
            self.opto.distance_correct = False  # for center
            self.opto.path_distance_correct = False  # total path
            self.opto.long_time_since_food = False
            self.opto.fly_moving = False
            self.opto.list_prev_y = [0]
            self.opto.list_prev_x = [0]

            self.opto.long_time_since_food = True
            self.opto.shouldCreateFood = False
            self.opto.time_of_last_food = None
            self.opto.time_since_last_food = None

        if self.stim is not None:
            self.stim.nextTrial(self._trial_dir)

        if self.flyplot is not None:
            self.flyplot.clear_plot()
            print('plot cleared')

    def _stop_trial(self):
        print('Stopped trial.')

        self.tracker.stopLogging()
        self.cam.stopLogging()
        self.tracker.stopTracking()
        self.trial_start_t = None
        self.trial_end_t = time()

        if self.opto is not None:
            self.opto.trial_start_t = self.trial_start_t
            self.opto.stopLogging()
            self.opto.foodspots = []
            self.opto.closest_food = None
            self.opto.fly_in_food = False

            self.opto.dist_from_center = None
            self.opto.total_distance = 0
            self.opto.distance_since_last_food = 0
            self.opto.closest_food = None
            self.opto.far_from_food = False
            self.opto.distance_correct = False  # for center
            self.opto.path_distance_correct = False  # total path
            self.opto.long_time_since_food = False
            self.opto.fly_moving = False
            self.opto.list_prev_y = [0]
            self.opto.list_prev_x = [0]

            self.opto.long_time_since_food = True
            self.opto.shouldCreateFood = False
            self.opto.time_of_last_food = None
            self.opto.time_since_last_food = None

        if self.stim is not None:
            self.stim.stopStim(self._trial_dir)

    def get_fly_pos(self):
        ### Get Fly Position ###

        if self.cam is not None and self.cam.fly is not None:
            camX = self.cam.fly.centerX
            camY = self.cam.fly.centerY
        else:
            camX = None
            camY = None

        if self.cnc is not None and self.cnc.status is not None:
            cncX = self.cnc.status.posX
            cncY = self.cnc.status.posY
        else:
            cncX = None
            cncY = None

        if camX is not None and cncX is not None:
            flyX = camX + cncX
            flyY = camY + cncY
        else:
            flyX = None
            flyY = None
        return flyX, flyY

    def get_fly_angle(self):
        fly_angle = None
        if self.cam is not None:
            fly = self.cam.fly
            if fly is not None:
                #fly_angle = 180-fly.angle
                fly_angle = fly.angle * 57.3  #fly angle is calculated in radians 57.3 is the conversion (roughly)

        return fly_angle

    def loopBody(self):
        if self.stim is not None:
            fly_pos_x, fly_pos_y = self.get_fly_pos()
            fly_angle = self.get_fly_angle()
            self.stim.updateStim(self._trial_dir, fly_pos_x=fly_pos_x, fly_pos_y=fly_pos_y, fly_angle=fly_angle)

        if self.state == 'started':
            if self.cam.flyPresent:
                print('Fly possibly found...')
                self.timer_start = time()
                self.state = 'fly detected'
                self.tracker.startTracking()
        elif self.state == 'fly detected':
            if (time() - self.timer_start) >= self.fly_detected_timeout:
                print('Fly found!')
                self.tracker.startTracking()
                self._start_trial()
                self.prev_state = 'fly detected'
                self.state = 'run'
                ## if fly is found make sure the gate is closed and if not, close it
                ##new part--verify works
                if self.dispenser is not None and self.dispenser.gate_state == 'open' and self.dispenser.gate_clear:
                  self.dispenser.trigger = 'auto'
                  self.dispenser.send_close_gate_command()
                  self.dispenser.state = 'Idle'
                  print('Dispenser: fly found, going to Idle state.')

            elif not self.cam.flyPresent:
                print('Fly lost.')
                self.timer_start = time()
                self.prev_state = 'fly detected'
                self.state = 'fly lost'

                self.tracker.stopTracking()
        elif self.state == 'run':
            if not self.cam.flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.prev_state = 'run'
                self.state = 'fly lost'
        elif self.state == 'fly lost':
            if self.cam.flyPresent:
                print('Fly located again.')
                self.timer_start = time()
                self.tracker.startTracking()
                if self.prev_state == 'run':
                    self.state = 'run'
                elif self.prev_state == 'fly detected':
                    self.state = 'fly detected'
            elif (time() - self.timer_start) >= self.fly_lost_timeout:
                if self.prev_state == 'run':
                    print('Fly is gone.')
                    self._stop_trial()
                self.tracker.start_moving_to_center()
                self.prev_state = 'fly lost'
                self.state = 'moving back to center'
        elif self.state == 'moving back to center':
            if self.tracker.is_close_to_center():
                if self.dispenser is not None:
                    self.dispenser.release_fly()
                else:
                    print('Dispenser not connected, please manually release fly')
                self.prev_state = 'moving back to center'
                self.state = 'started'
        else:
            raise Exception('Invalid state.')