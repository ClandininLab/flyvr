import sys
import cv2
from time import strftime, time, sleep

from PyQt5.QtWidgets import QApplication, QMessageBox, QInputDialog, QWidget, QPushButton
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5 import QtGui
from functools import partial
from PyQt5.QtCore import QSize

from flyrpc.launch import launch_server
from flyvr.service import Service

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
import flyvr.dispenser
from flyvr.opto import OptoThread
from flyvr.stim import StimThread
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
        self.stim = None

        # Set background services to none
        self.trial = None
        self.tracker = None

        self.frameData = None

        self.ui.thresh_slider.valueChanged.connect(partial(self.valuechg, self.ui))
        self.ui.thresh_slider.setValue(99)

        self.cnc_shouldinitialize = None
        self.ask_cnc_init = True
        self.cncinit = False
        self.message = []

        # Setup cnc buttons
        self.ui.cnc_start_button.clicked.connect(lambda x: self.cncStart())
        self.ui.cnc_stop_button.clicked.connect(lambda x: self.cncStop())
        self.ui.cnc_initialize_button.clicked.connect(lambda x: self.initializeCnc())
        self.ui.cnc_move_center_button.clicked.connect(lambda x: self.tracker.move_to_center())
        self.ui.cnc_mark_center_button.clicked.connect(lambda x: self.markCenter())
        self.ui.cnc_initialize_button.setEnabled(False)
        self.ui.cnc_move_center_button.setEnabled(False)
        self.ui.cnc_mark_center_button.setEnabled(False)
        # Setup cnc movement buttons
        self.ui.cnc_up_button.pressed.connect(lambda: self.tracker.manual_move_up())
        self.ui.cnc_up_button.released.connect(lambda: self.tracker.manual_stop())
        self.ui.cnc_down_button.pressed.connect(lambda: self.tracker.manual_move_down())
        self.ui.cnc_down_button.released.connect(lambda: self.tracker.manual_stop())
        self.ui.cnc_right_button.pressed.connect(lambda: self.tracker.manual_move_right())
        self.ui.cnc_right_button.released.connect(lambda: self.tracker.manual_stop())
        self.ui.cnc_left_button.pressed.connect(lambda: self.tracker.manual_move_left())
        self.ui.cnc_left_button.released.connect(lambda: self.tracker.manual_stop())
        self.ui.cnc_up_button.setEnabled(False)
        self.ui.cnc_down_button.setEnabled(False)
        self.ui.cnc_left_button.setEnabled(False)
        self.ui.cnc_right_button.setEnabled(False)

        # Setup cam buttons
        self.ui.camera_start_button.clicked.connect(lambda x: self.camStart())
        self.ui.camera_stop_button.clicked.connect(lambda x: self.camStop())

        # Setup visual stimulus buttons
        self.ui.stim_start_button.clicked.connect(lambda x: self.stimStart())

        # Setup dispenser buttons
        self.ui.dispenser_start_button.clicked.connect(lambda x: self.dispenserStart())
        self.ui.dispenser_stop_button.clicked.connect(lambda x: self.dispenserStop())
        self.ui.open_gate_button.clicked.connect(lambda x: self.dispenser.open_gate())
        self.ui.close_gate_button.clicked.connect(lambda x: self.dispenser.close_gate())
        self.ui.close_gate_button.setEnabled(False)
        self.ui.open_gate_button.setEnabled(False)

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
        self.ui.stop_experiment_button.clicked.connect(lambda x: self.experimentStop())

        # Setup trial buttons
        self.ui.start_trial_button.clicked.connect(lambda x: self.trialStart())
        self.ui.stop_trial_button.clicked.connect(lambda x: self.trialStop())
        self.ui.start_trial_button.setEnabled(False)
        self.ui.stop_trial_button.setEnabled(False)

        #Setup quickstart button
        self.ui.quick_start_button.clicked.connect(lambda x: self.quickStart())

    def valuechg(self, data):
        self.ui.thresh_label.setText(str(data))

    def dispenserStart(self):
        self.dispenser = launch_server(flyvr.dispenser)
        self.ui.dispenser_start_button.setEnabled(False)
        self.ui.dispenser_stop_button.setEnabled(True)
        self.ui.close_gate_button.setEnabled(True)
        self.ui.open_gate_button.setEnabled(True)

    def dispenserStop(self):
        #how to turn off?
        self.ui.dispenser_start_button.setEnabled(True)
        self.ui.dispenser_stop_button.setEnabled(False)
        self.ui.close_gate_button.setEnabled(False)
        self.ui.open_gate_button.setEnabled(False)

    def cncStart(self):
        if self.ask_cnc_init:
            mail = Mail()
            CncPopup(mail)
            self.cnc_shouldinitialize = mail.message
            if self.cnc_shouldinitialize:
                cnc_home()
                self.cncinit = True
        else:
            cnc_home()
        self.cnc = CncThread()
        self.cnc.start()
        sleep(0.1)
        self.trackerStart()
        self.ui.cnc_start_button.setEnabled(False)
        self.ui.cnc_stop_button.setEnabled(True)
        self.ui.cnc_initialize_button.setEnabled(True)
        self.ui.cnc_move_center_button.setEnabled(True)
        self.ui.cnc_mark_center_button.setEnabled(True)

    def cncStop(self):
        self.cnc.stop()
        self.trackerStop()
        self.ui.cnc_start_button.setEnabled(True)
        self.ui.cnc_stop_button.setEnabled(False)
        self.ui.cnc_initialize_button.setEnabled(False)
        self.ui.cnc_move_center_button.setEnabled(False)
        self.ui.cnc_mark_center_button.setEnabled(False)

    def initializeCnc(self):
        self.cnc.stop()
        self.tracker.stop()
        cnc_home()
        self.cnc = CncThread()
        self.cnc.start()
        sleep(0.1)
        self.trackerStart()
        self.tracker.move_to_center()
        self.cncinit = True

    def markCenter(self):
        self.tracker.set_center_pos(self.cnc.status.posX, self.cnc.status.posY)
        self.cncinit = True

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
        if self.cnc_shouldinitialize:
            self.tracker.move_to_center()
        self.ui.cnc_up_button.setEnabled(True)
        self.ui.cnc_down_button.setEnabled(True)
        self.ui.cnc_left_button.setEnabled(True)
        self.ui.cnc_right_button.setEnabled(True)

    def trackerStop(self):
        self.tracker.stop()
        self.ui.cnc_up_button.setEnabled(False)
        self.ui.cnc_down_button.setEnabled(False)
        self.ui.cnc_left_button.setEnabled(False)
        self.ui.cnc_right_button.setEnabled(False)

    def stimStart(self):
        self.stim = StimThread()

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

    def experimentStart(self):
        if self.cam is None:
            self.message.append("Turn on the camera before starting the experiment.")
        if self.cnc is None:
            self.message.append("Turn on the cnc before starting the experiment.")
        if not self.cncinit:
            self.message.append("Initialize cnc or mark center before starting the experiment.")
        if self.message:
            print(self.message)
            MessagePopup(self.message)
            self.message = []
        else:
            self.trial = TrialThread(cam=self.cam, dispenser=self.dispenser, cnc=self.cnc, tracker=self.tracker,
                                           opto=self.opto, stim=self.stim, ui=self.ui)
            self.trial.start()
            if self.dispenser is not None:
                self.dispenser.release_fly()
            self.ui.start_experiment_button.setEnabled(False)
            self.ui.stop_experiment_button.setEnabled(True)
            self.ui.stop_trial_button.setEnabled(True)

    def experimentStop(self):
        self.trial._stop_trial()
        self.trial.stop()
        self.ui.start_experiment_button.setEnabled(True)
        self.ui.stop_experiment_button.setEnabled(False)
        self.ui.start_trial_button.setEnabled(False)
        self.ui.stop_trial_button.setEnabled(False)

    def trialStart(self):
        self.trial._start_trial()
        self.ui.start_trial_button.setEnabled(False)
        self.ui.stop_trial_button.setEnabled(True)

    def trialStop(self):
        self.trial._stop_trial()
        self.ui.start_trial_button.setEnabled(True)
        self.ui.stop_trial_button.setEnabled(False)

    def quickStart(self):
        self.ui.quick_start_button.setEnabled(False)
        self.cnc_shouldinitialize = True
        self.ask_cnc_init = False
        self.camStart()
        self.cncStart()

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
        if self.trial is not None:
            self.trial._stop_trial()
            self.trial.stop()
        if self.dispenser is not None:
            pass
        print('Shutdown Called')

class Mail():
    def __init__(self):
        message = None

class CncPopup(QMessageBox):
    def __init__(self, mail):
        super().__init__()
        self.title = 'box thing'
        self.left = 10
        self.top = 10
        self.width = 320
        self.height = 200
        self.initUI(mail)
    def initUI(self, mail):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        buttonReply = QMessageBox.question(self, 'CNC Control', "Would you like to initialize the CNC?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            mail.message = True
        else:
            mail.message = False
        self.show()

class MessagePopup(QMessageBox):
    def __init__(self, message):
        super().__init__()
        self.title = 'box thing'
        self.left = 600
        self.top = 400
        self.width = 320
        self.height = 200
        self.initUI(message)
    def initUI(self, message):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        QMessageBox.warning(self, 'Warning', '\n\n'.join(message))
        self.show()

# class MessagePopup(QMessageBox):
#     def __init__(self):
#         super().__init__()
#         self.title = 'box thing'
#         self.left = 10
#         self.top = 10
#         self.width = 320
#         self.height = 200
#
#         #self.setMinimumSize(QSize(300, 200))
#         self.setWindowTitle("PyQt messagebox example - pythonprogramminglanguage.com")
#         self.setGeometry(self.left, self.top, self.width, self.height)
#
#         pybutton = QPushButton('Show messagebox', self)
#         pybutton.clicked.connect(self.clickMethod)
#         pybutton.resize(200,64)
#         pybutton.move(50, 50)
#         self.show()
#
#     def clickMethod(self):
#         QMessageBox.about(self, "Title", "Message")

def main():
    app = QApplication(sys.argv)
    dialog = QtWidgets.QMainWindow()
    prog = MainGui(dialog)
    #sys.exit(app.exec_())
    sys.exit(prog.shutdown(app))

if __name__ == '__main__':
    main()

