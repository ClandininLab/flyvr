import sys
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from functools import partial

import flyvr.gate_control
from flyvr.opto import OptoThread
from flyrpc.launch import launch_server

class MainGui():
    def __init__(self):

        app = QApplication(sys.argv)

        self.ui = uic.loadUi('main.ui')

        self.ui.show()

        # Set services to none
        self.dispenser = None
        self.opto = None
        self.cam = None
        self.cnc = None
        self.tracker = None
        self.stim = None

        self.ui.thresh_slider.valueChanged.connect(partial(valuechg, self.ui))
        self.ui.thresh_slider.setValue(99)

        # Setup cnc buttons
        self.ui.cnc_start_button.clicked.connect(lambda x: cncStart())

        # Setup cam buttons
        self.ui.camera_start_button.clicked.connect(lambda x: camStart())

        # Setup visual stimulus buttons
        self.ui.stim_start_button.clicked.connect(lambda x: stimStart())

        # Setup dispenser buttons
        self.ui.dispenser_start_button.clicked.connect(lambda x: dispenserStart())
        self.ui.dispenser_stop_button.clicked.connect(lambda x: dispenserStop())
        self.ui.start_trial_button.clicked.connect(lambda x: self.dispenser.release_fly())
        self.ui.open_gate_button.clicked.connect(lambda x: self.dispenser.open_gate())
        self.ui.close_gate_button.clicked.connect(lambda x: self.dispenser.close_gate())

        # Setup opto buttons
        self.ui.opto_start_button.clicked.connect(lambda x: optoStart())
        self.ui.opto_on_button.clicked.connect(lambda x: opto.on())
        self.ui.opto_off_button.clicked.connect(lambda x: opto.off())
        self.ui.opto_pulse_button.clicked.connect(lambda x: opto.pulse())

        # Setup main experiment buttons
        self.ui.start_experiment_button.clicked.connect(lambda x: experimentStart())

        # TRY WITHOUT LAMBDAS AND WITHOUT ()

    def valuechg(self, data):
        ui.thresh_label.setText(str(data))

    def dispenserStart(self):
        self.dispenser = launch_server(flyvr.gate_control)
        self.ui.dispenser_start_button.setEnabled(False)
        self.ui.dispenser_stop_button.setEnabled(True)

    def dispenserStop(self):
        pass

    def cncStart(self):
        self.cnc = CncThread()
        self.cnc.start()

    def camStart(self):
        self.cam = CamThread()
        self.cam.start()

    def stimStart(self):
        self.stim = MrDisplay()

    def optoStart(self):
        self.opto = OptoThread(cncThread=self.cnc, camThread=self.cam,
                               TrackThread=self.tracker)
        self.opto.start()

    def trackerStart(self):
        self.tracker = TrackThread(cncThread=self.cnc, camThread=self.cam)
        self.tracker.start()

    def experimentStart(self):
        self.trialThread = TrialThread(cam=self.cam, dispenser=self.dispenser,
                                       mrstim=self.mrstim, opto=self.opto, stim=self.stim, ui=self.ui)
        self.trialThread.start()

    sys.exit(app.exec_())

def main():
    MainGui()

if __name__ == '__main__':
    main()

