import os
import os.path
import itertools
import xmlrpc.client

from time import strftime, perf_counter, time, sleep
from functools import partial

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
from flyvr.service import Service

import sys
import types
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from PyQt5.QtCore import QBasicTimer

from threading import Lock

class Smooth:
    def __init__(self, n):
        self.n = n
        self.hist = [0]*n

    def update(self, value):
        self.hist = [float(value)] + self.hist[:-1]
        return sum(self.hist)/self.n

class TrialThread(Service):
    def __init__(self, exp_dir, loopTime=10e-3, fly_lost_timeout=1, fly_found_timeout=1):
        self.trial_count = itertools.count(1)
        self.state = 'manual'

        # start the tracker thread
        self.tracker = TrackThread()
        self.tracker.start()

        # Camera thread
        self.camLock = Lock()
        self._cam = None

        # CNC thread
        self.cncLock = Lock()
        self._cnc = None

        # Stimulus thread
        self.stimLock = Lock()
        self._stim = None

        # Dispenser thread
        self.dispLock = Lock()
        self._dispenser = None

        self.timer_start = None

        self.exp_dir = exp_dir
        self.fly_lost_timeout = fly_lost_timeout
        self.fly_found_timeout = fly_found_timeout

        # set up access to the thread-ending signal
        self.manualLock = Lock()
        self._manualCmd = None

        self.trialDirLock = Lock()
        self._trial_dir = None

        # call constructor from parent
        super().__init__(minTime=loopTime, maxTime=loopTime)

    @property
    def cam(self):
        with self.camLock:
            return self._cam

    @cam.setter
    def cam(self, value):
        with self.camLock:
            self._cam = value
        self.tracker.cam = value

    @property
    def cnc(self):
        with self.cncLock:
            return self._cnc

    @cnc.setter
    def cnc(self, value):
        with self.cncLock:
            self._cnc = value
        self.tracker.cnc = value

    @property
    def stim(self):
        with self.stimLock:
            return self._stim

    @stim.setter
    def stim(self, value):
        with self.stimLock:
            self._stim = value

    @property
    def dispenser(self):
        with self.dispLock:
            return self._dispenser

    @dispenser.setter
    def dispenser(self, value):
        with self.dispLock:
            self._dispenser = value

    @property
    def manualCmd(self):
        with self.manualLock:
            return self._manualCmd

    def resetManual(self):
        with self.manualLock:
            self._manualCmd = None

    def manual(self, *args):
        with self.manualLock:
            self._manualCmd = args

    def stop(self):
        super().stop()
        self.tracker.stop()

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

        if self.cnc is not None:
            self.cnc.startLogging(os.path.join(_trial_dir, 'cnc.txt'))

        if self.cam is not None:
            self.cam.startLogging(os.path.join(_trial_dir, 'cam.txt'),
                                  os.path.join(_trial_dir, 'cam_uncompr.mkv'),
                                  os.path.join(_trial_dir, 'cam_compr.mkv'))

        self._trial_dir = _trial_dir

    def _stop_trial(self):
        print('Stopped trial.')

        if self.cnc is not None:
            self.cnc.stopLogging()

        if self.cam is not None:
            self.cam.stopLogging()

    def loopBody(self):
        flyData = self.cam.flyData if (self.cam is not None) else None
        flyPresent = flyData.flyPresent if (flyData is not None) else None

        if self.state == 'started':
            if self.manualCmd is not None:
                self.state = 'manual'
                print('** manual **')
            elif flyPresent:
                print('Fly possibly found...')
                self.timer_start = time()
                self.state = 'fly_found'
                print('** fly_found **')
                self.tracker.startTracking()
        elif self.state == 'fly_found':
            if self.manualCmd is not None:
                self.tracker.stopTracking()
                self.state = 'manual'
                print('** manual **')
            elif not flyPresent:
                print('Fly lost.')
                self.state = 'started'
                print('** started **')
                self.tracker.stopTracking()
                self.tracker.move_to_center()
            elif (time() - self.timer_start) >= self.fly_found_timeout:
                print('Fly found.')
                self._start_trial()
                self.state = 'run'
                print('** run **')
        elif self.state == 'run':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif not flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.state = 'fly_lost'
                print('** fly_lost **')
        elif self.state == 'fly_lost':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif flyPresent:
                print('Fly located again.')
                self.state = 'run'
                print('** run **')
            elif (time() - self.timer_start) >= self.fly_lost_timeout:
                print('Fly lost.')
                self._stop_trial()
                self.tracker.move_to_center()
                self.state = 'started'
                print('** started **')
        elif self.state == 'manual':
            manualCmd = self.manualCmd

            if manualCmd is None:
                pass
            elif manualCmd[0] == 'start':
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
            else:
                raise Exception('Invalid manual command.')

            if (manualCmd is not None) and (manualCmd[0] != 'jog'):
                self.resetManual()
        else:
            raise Exception('Invalid state.')

def main():
    # create folder for data
    topdir = r'E:\FlyVR'
    folder = 'exp-'+strftime('%Y%m%d-%H%M%S')
    exp_dir = os.path.join(topdir, folder)
    os.makedirs(exp_dir)

    # settings for UI
    tUpdate = 0.1
    absJogVel = 0.01

    # load the UI
    app = QApplication(sys.argv)

    this_file_path = os.path.realpath(os.path.expanduser(__file__))
    qt_dir = os.path.join(os.path.dirname(os.path.dirname(this_file_path)), 'qt')
    gui = uic.loadUi(os.path.join(qt_dir, 'main.ui'))

    # Run trial manager
    trialThread = TrialThread(exp_dir=exp_dir)
    trialThread.start()

    # Other threads
    cam = None
    cnc = None
    stim = None
    dispenser = None

    # jogging
    def jog(manVelX, manVelY):
        trialThread.manual('jog', manVelX, manVelY)
    def nojog():
        trialThread.manual('nojog')

    gui.cnc_up_button.pressed.connect(partial(jog, 0, +absJogVel))
    gui.cnc_down_button.pressed.connect(partial(jog, 0, -absJogVel))
    gui.cnc_right_button.pressed.connect(partial(jog, -absJogVel, 0))
    gui.cnc_left_button.pressed.connect(partial(jog, +absJogVel, 0))

    gui.cnc_up_button.released.connect(nojog)
    gui.cnc_down_button.released.connect(nojog)
    gui.cnc_right_button.released.connect(nojog)
    gui.cnc_left_button.released.connect(nojog)

    # Live GUI updates
    def timerEvent(self, e):
        # display CNC status
        cncStatus = cnc.status if (cnc is not None) else None
        print(cncStatus)
        gui.cnc_x_label.setText(str(cncStatus.posX * 1e3) if (cncStatus is not None) else 'N/A')
        gui.cnc_y_label.setText(str(cncStatus.posY * 1e3) if (cncStatus is not None) else 'N/A')

        # display fly status
        flyData = cam.flyData if cam else None
        gui.fly_minor_axis_label.setText(str(flyData.ma * 1e3) if (flyData is not None) else 'N/A')
        gui.fly_major_axis_label.setText(str(flyData.MA * 1e3) if (flyData is not None) else 'N/A')
        gui.fly_aspect_ratio_label.setText(str(flyData.ma / flyData.MA) if (flyData is not None) else 'N/A')
        gui.fly_x_label.setText(str(flyData.flyX * 1e3) if (flyData is not None) else 'N/A')
        gui.fly_y_label.setText(str(flyData.flyY * 1e3) if (flyData is not None) else 'N/A')

    gui.timerEvent = types.MethodType(timerEvent, gui)
    timer = QBasicTimer()
    timer.start(int(tUpdate*1e3), gui)

    # mark center position
    def mark_center():
        cncStatus = cnc.status if cnc else None
        if cncStatus is not None:
            posX, posY = cncStatus.posX, cncStatus.posY
            trialThread.tracker.set_center_pos(posX=posX, posY=posY)

    gui.cnc_mark_center_button.clicked.connect(mark_center)

    # move to center
    gui.cnc_move_center_button.clicked.connect(partial(trialThread.manual, 'center'))

    # start trial
    def start_trial():
        trialThread.manual('start')
        gui.start_trial_button.setEnabled(False)
        gui.stop_trial_button.setEnabled(True)
    gui.start_trial_button.clicked.connect(start_trial)

    # stop trial
    def stop_trial():
        trialThread.manual('stop')
        gui.start_trial_button.setEnabled(True)
        gui.stop_trial_button.setEnabled(False)
    gui.stop_trial_button.clicked.connect(stop_trial)

    # threshold slider
    def slider_to_thresh(pos):
        return pos + 1
    def thresh_action(pos):
        if cam is not None:
            cam.threshold = slider_to_thresh(pos)
        gui.thresh_label.setText(str(pos))
    gui.thresh_slider.valueChanged.connect(thresh_action)
    gui.thresh_slider.setValue(115)

    # aspect ratio (min)
    def slider_to_aspect_ratio(pos):
        return pos/10.0
    def r_min_action(pos):
        if (cam is not None) and (cam.cam is not None):
            cam.cam.r_min = slider_to_aspect_ratio(pos)
        gui.r_min_label.setText(str(pos))
    gui.r_min_slider.valueChanged.connect(r_min_action)
    gui.r_min_slider.setValue(2)

    # aspect ratio (max)
    def r_max_action(pos):
        if (cam is not None) and (cam.cam is not None):
            cam.cam.r_max = slider_to_aspect_ratio(pos)
        gui.r_max_label.setText(str(pos))
    gui.r_max_slider.valueChanged.connect(r_max_action)
    gui.r_max_slider.setValue(5)

    # loop gain
    def slider_to_loop_gain(pos):
        return 0.1*pos
    def loop_gain_action(pos):
        trialThread.tracker.a = slider_to_loop_gain(pos)
        gui.loop_gain_label.setText(str(pos))
    gui.loop_gain_slider.valueChanged.connect(loop_gain_action)
    gui.loop_gain_slider.setValue(100)

    # CNC service
    def start_cnc():
        gui.cnc_start_button.setEnabled(False)
        cnc_home()
        cnc = CncThread()
        cnc.start()
        trialThread.cnc = cnc
        gui.cnc_stop_button.setEnabled(True)
    gui.cnc_start_button.clicked.connect(start_cnc)

    def stop_cnc():
        gui.cnc_stop_button.setEnabled(False)
        trialThread.cnc = None
        cnc.stop()
        gui.cnc_start_button.setEnabled(True)
    gui.cnc_stop_button.clicked.connect(stop_cnc)

    # display the GUI
    gui.show()

    # run the application
    exit_code = app.exec_()

    trialThread.stop()

    if cnc is not None:
        cnc.stop()

    if cam is not None:
        cam.stop()

    sys.exit(exit_code)
        
if __name__ == '__main__':
    main()