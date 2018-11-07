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
    def __init__(self, exp_dir, cam, dispenser, mrstim, opto, cnc, tracker, ui,
                 loopTime=10e-3, fly_lost_timeout=2, fly_detected_timeout=2, auto_change_rate=None):

        self.trial_count = itertools.count(1)
        self.state = 'startup'
        self.prev_state = 'startup'

        self.cam = cam
        self.cnc = cnc
        self.dispenser = dispenser
        self.mrstim = mrstim
        self.opto = opto
        self.ui = ui
        self.tracker = tracker

        self.timer_start = None

        self.exp_dir = exp_dir
        self.fly_lost_timeout = fly_lost_timeout
        self.fly_detected_timeout = fly_detected_timeout
        self.auto_change_rate = auto_change_rate

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
        folder = 'exp-'+strftime('%Y%m%d-%H%M%S')
        exp_dir = os.path.join(topdir, folder)
        os.makedirs(exp_dir)

        # start logging to dispenser
        #try:
        #    self.dispenser.start_logging(self.exp_dir)
        #except OSError:
        #    print('Could not set up dispenser logging.')

        # call constructor from parent
        super().__init__(minTime=loopTime, maxTime=loopTime, iter_warn=False)

    def stop(self):
        super().stop()
        self.tracker.stop()
        self.cnc.stop()

    @property
    def trial_dir(self):
        with self.trialDirLock:
            return self._trial_dir

    def _start_trial(self):
        trial_num = next(self.trial_count)
        print('Started trial ' + str(trial_num))
        folder = 'trial-' + str(trial_num) + '-' + strftime('%Y%m%d-%H%M%S')
        _trial_dir = os.path.join(self.exp_dir, folder)
        os.makedirs(_trial_dir)

        self.cnc.startLogging(os.path.join(_trial_dir, 'cnc.txt'))
        self.cam.startLogging(os.path.join(_trial_dir, 'cam.txt'),os.path.join(_trial_dir, 'cam_compr.mkv'))
        self.opto.startLogging(os.path.join(_trial_dir, 'opto.txt'))

        self._trial_dir = _trial_dir
        self.mrstim.nextStim(self._trial_dir)

    def _stop_trial(self):
        print('Stopped trial.')

        self.cnc.stopLogging()
        self.cam.stopLogging()
        self.mrstim.stopStim(self._trial_dir)

        self.tracker.stopTracking()

    def loopBody(self):
        #self.mrstim.updateStim(self._trial_dir)

        if self.state == 'startup':
            print('** startup **')
            # go to the manual control state
            self.resetManual()
            self.state = 'manual'
            print('** manual **')
        elif self.state == 'started':
            if self.manualCmd is not None:
                self.state = 'manual'
                print('** manual **')
            elif self.cam.flyData.flyPresent:
                print('Fly possibly found...')
                self.timer_start = time()
                self.state = 'fly detected'
                self.tracker.startTracking()
        elif self.state == 'fly detected':
            if self.manualCmd is not None:
                self.tracker.stopTracking()
                self.prev_state = 'fly detected'
                self.state = 'manual'
                print('** manual **')
            elif (time() - self.timer_start) >= self.fly_detected_timeout:
                print('Fly found!')
                self.tracker.startTracking()
                self._start_trial()
                self.prev_state = 'fly detected'
                self.state = 'run'
                #print('** run **')
            elif not self.cam.flyData.flyPresent:
                print('Fly lost.')
                self.timer_start = time()
                self.prev_state = 'fly detected'
                self.state = 'fly lost'
                self.tracker.stopTracking()
        elif self.state == 'run':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif not self.cam.flyData.flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.prev_state = 'run'
                self.state = 'fly lost'
        elif self.state == 'fly lost':
            if self.manualCmd is not None:
                self._stop_trial()
                self.prev_state = 'fly lost'
                self.state = 'manual'
                print('** manual **')
            elif self.cam.flyData.flyPresent:
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
                self.tracker.move_to_center()
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
                self.prev_state = 'fly lost'
                self.state = 'started'
        elif self.state == 'manual':
            manualCmd = self.manualCmd

            if manualCmd is None:
                pass
            elif manualCmd[0] == 'start':
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
                self.state = 'started'
                print('** started **')
            elif manualCmd[0] == 'stop':
                print('** manual: stop **')
            elif manualCmd[0] == 'center':
                print('** manual: center **')
                self.tracker.move_to_center()
            elif manualCmd[0] == 'nojog':
                print('** manual: nojog **')
                self.tracker.manualVelocity = None
            elif manualCmd[0] == 'jog':
                manualVelocity = ManualVelocity(velX=manualCmd[1], velY=manualCmd[2])
                self.tracker.manualVelocity = manualVelocity
            elif manualCmd[0] == 'release_fly':
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
            else:
                raise Exception('Invalid manual command.')

            if (manualCmd is not None) and (manualCmd[0] != 'jog'):
                self.resetManual()
        else:
            raise Exception('Invalid state.')