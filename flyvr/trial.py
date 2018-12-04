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
    def __init__(self, cam, dispenser, stim, opto, tracker, ui,
                 loopTime=10e-3, fly_lost_timeout=2, fly_detected_timeout=2):

        self.trial_count = itertools.count(1)
        self.state = 'started'
        self.prev_state = 'started'

        self.cam = cam
        self.dispenser = dispenser
        self.stim = stim
        self.opto = opto
        self.ui = ui
        self.tracker = tracker

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

        if self.stim is not None:
            self.stim.nextTrial(self._trial_dir)

    def _stop_trial(self):
        print('Stopped trial.')

        self.tracker.stopLogging()
        self.cam.stopLogging()
        self.tracker.stopTracking()
        self.trial_start_t = None
        self.trial_end_t = time()

        if self.opto is not None:
            self.opto.stopLogging()

        if self.stim is not None:
            self.stim.stopStim(self._trial_dir)

    def get_fly_pos(self):
        cam_x, cam_y = None, None
        if self.cam is not None:
            flyData = self.cam.flyData
            if flyData is not None and flyData.flyPresent:
                cam_x, cam_y = flyData.flyX, flyData.flyY

        if cam_x is None or cam_y is None:
            return None, None

        cnc_x = None
        cnc_y = None
        if self.tracker is not None and self.tracker.cncThread is not None:
            status = self.tracker.cncThread.status
            if status is not None:
                cnc_x, cnc_y = status.posX, status.posY

        if cnc_x is None or cnc_y is None:
            return None, None

        # NOTE: this is not an error!  The coordinate definitions of X and Y are flipped for screen definitions
        # as compared to the CNC and camera axes
        fly_y = cam_x + cnc_x
        fly_x = cam_y + cnc_y

        return fly_x, fly_y

    def get_fly_angle(self):
        fly_angle = None
        if self.cam is not None:
            fly_data = self.cam.flyData
            if fly_data is not None:
                fly_angle = 180-fly_data.angle

        return fly_angle

    def loopBody(self):
        if self.stim is not None:
            fly_pos_x, fly_pos_y = self.get_fly_pos()
            fly_angle = self.get_fly_angle()
            self.stim.updateStim(self._trial_dir, fly_pos_x=fly_pos_x, fly_pos_y=fly_pos_y, fly_angle=fly_angle)

        if self.state == 'started':
            if self.cam.flyData.flyPresent:
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
            elif not self.cam.flyData.flyPresent:
                print('Fly lost.')
                self.timer_start = time()
                self.prev_state = 'fly detected'
                self.state = 'fly lost'
                self.tracker.stopTracking()
        elif self.state == 'run':
            if not self.cam.flyData.flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.prev_state = 'run'
                self.state = 'fly lost'
        elif self.state == 'fly lost':
            if self.cam.flyData.flyPresent:
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