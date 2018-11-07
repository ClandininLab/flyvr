import sys
import cv2
from time import strftime, time, sleep

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5 import QtGui
from functools import partial

from flyrpc.launch import launch_server
from flyvr.service import Service

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
import flyvr.gate_control
from flyvr.opto import OptoThread
from flyvr.mrstim import MrDisplay
from flyvr.trial import TrialThread

class MainGui():
    def __init__(self, dialog):

        self.ui = uic.loadUi('main.ui')
        self.ui.show()

        # Set services to none
        self.dispenser = None
        self.opto = None
        self.cam = None
        self.cnc = None
        self.tracker = None
        self.stim = None

        self.frameData = None

        self.ui.thresh_slider.valueChanged.connect(partial(self.valuechg, self.ui))
        self.ui.thresh_slider.setValue(99)

        # Setup cnc buttons
        self.ui.cnc_start_button.clicked.connect(lambda x: self.cncStart())
        self.ui.cnc_stop_button.clicked.connect(lambda x: self.cncStop())

        # Setup cam buttons
        self.ui.camera_start_button.clicked.connect(lambda x: self.camStart())
        self.ui.camera_stop_button.clicked.connect(lambda x: self.camStop())

        # Setup tracker buttons
        self.ui.tracker_start_button.clicked.connect(lambda x: self.trackerStart())
        self.ui.tracker_stop_button.clicked.connect(lambda x: self.trackerStop())

        # Setup visual stimulus buttons
        self.ui.stim_start_button.clicked.connect(lambda x: self.stimStart())

        # Setup dispenser buttons
        self.ui.dispenser_start_button.clicked.connect(lambda x: self.dispenserStart())
        self.ui.dispenser_stop_button.clicked.connect(lambda x: self.dispenserStop())
        self.ui.open_gate_button.clicked.connect(lambda x: self.dispenser.open_gate())
        self.ui.close_gate_button.clicked.connect(lambda x: self.dispenser.close_gate())

        # Setup opto buttons
        self.ui.opto_start_button.clicked.connect(lambda x: self.optoStart())
        self.ui.opto_stop_button.clicked.connect(lambda x: self.optoStop())
        self.ui.opto_on_button.clicked.connect(lambda x: self.opto.on())
        self.ui.opto_off_button.clicked.connect(lambda x: self.opto.off())
        self.ui.opto_pulse_button.clicked.connect(lambda x: self.opto.pulse())
        self.ui.opto_stop_button.setEnabled(False)
        self.ui.opto_on_button.setEnabled(False)
        self.ui.opto_off_button.setEnabled(False)
        self.ui.opto_pulse_button.setEnabled(False)

        # Setup main experiment buttons
        self.ui.start_experiment_button.clicked.connect(lambda x: self.experimentStart())

    def valuechg(self, data):
        self.ui.thresh_label.setText(str(data))

    def dispenserStart(self):
        self.dispenser = launch_server(flyvr.gate_control)
        self.ui.dispenser_start_button.setEnabled(False)
        self.ui.dispenser_stop_button.setEnabled(True)

    def dispenserStop(self):
        pass

    def cncStart(self):
        cnc_home()
        self.cnc = CncThread()
        self.cnc.start()
        sleep(0.1)
        self.ui.cnc_start_button.setEnabled(False)
        self.ui.cnc_start_button.setEnabled(True)

    def cncStop(self):
        self.cnc.stop()
        self.ui.cnc_start_button.setEnabled(True)
        self.ui.cnc_start_button.setEnabled(False)

    def camStart(self):
        cv2.namedWindow('image')
        self.cam = CamThread()
        self.cam.start()
        self.ui.camera_start_button.setEnabled(False)
        self.ui.camera_stop_button.setEnabled(True)

    def camStop(self):
        self.cam.cam.camera.StopGrabbing()
        self.cam.stop()
        cv2.destroyAllWindows()
        self.ui.camera_start_button.setEnabled(True)
        self.ui.camera_stop_button.setEnabled(False)

    def trackerStart(self):
        self.tracker = TrackThread(cncThread=self.cnc, camThread=self.cam)
        self.tracker.start()
        self.tracker.move_to_center()
        self.ui.tracker_start_button.setEnabled(False)
        self.ui.tracker_stop_button.setEnabled(True)

    def trackerStop(self):
        self.tracker.stop()
        self.ui.tracker_start_button.setEnabled(True)
        self.ui.tracker_stop_button.setEnabled(False)

    def stimStart(self):
        self.stim = MrDisplay()

    def optoStart(self):
        self.opto = OptoThread(cncThread=self.cnc, camThread=self.cam,
                               TrackThread=self.tracker)
        self.opto.start()
        self.ui.opto_start_button.setEnabled(False)
        self.ui.opto_stop_button.setEnabled(True)
        self.ui.opto_on_button.setEnabled(True)
        self.ui.opto_off_button.setEnabled(True)
        self.ui.opto_pulse_button.setEnabled(True)

    def optoStop(self):
        self.opto.stop()
        self.ui.opto_start_button.setEnabled(True)
        self.ui.opto_stop_button.setEnabled(False)
        self.ui.opto_on_button.setEnabled(False)
        self.ui.opto_off_button.setEnabled(False)
        self.ui.opto_pulse_button.setEnabled(False)

    def trackerStart(self):
        self.tracker = TrackThread(cncThread=self.cnc, camThread=self.cam)
        self.tracker.start()

    def experimentStart(self):
        self.trialThread = TrialThread(cam=self.cam, dispenser=self.dispenser,
                                       mrstim=self.mrstim, opto=self.opto, stim=self.stim, ui=self.ui)
        self.trialThread.start()

    def shutdown(self, app):
        app.exec_()
        if self.opto is not None:
            self.opto.off()
            self.opto.stop()
        if self.cam is not None:
            self.cam.stop()
            cv2.destroyAllWindows()
        if self.cnc is not None:
            self.cnc.stop()
        if self.tracker is not None:
            self.tracker.stop()
        print('Shutdown Called')

def main():
    app = QApplication(sys.argv)
    dialog = QtWidgets.QMainWindow()
    prog = MainGui(dialog)
    #sys.exit(app.exec_())
    sys.exit(prog.shutdown(app))

if __name__ == '__main__':
    main()

