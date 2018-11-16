import sys
import cv2
import numpy as np
from time import strftime, time, sleep
from threading import Thread, Lock, Event
import random

#from matplotlib.backends.qt_compat import QtCore, QtWidgets
#from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
#from matplotlib.figure import Figure

from PyQt5.QtWidgets import QApplication, QMessageBox, QInputDialog, QWidget, QPushButton, QSizePolicy
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5 import QtGui, QtCore
from functools import partial
from PyQt5.QtCore import QSize, QFile, QTextStream

from flyrpc.launch import launch_server
from flyvr.service import Service

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
from flyvr.dispenser import FlyDispenser
from flyvr.opto import OptoThread
from flyvr.stim import StimThread
from flyvr.trial import TrialThread
from qt.plotting import PlotWindow, ImgWindow
from qt.gui import GuiThread

class MainGui():
    def __init__(self, dialog):

        self.ui = uic.loadUi('main.ui')
        self.ui.show()
        #self.left = 600
        #self.top = 400

        # Set services to none
        self.dispenser = None
        self.opto = None
        self._cam = None
        self.stim = None

        # Set background services to none
        self.trial = None
        self.tracker = None

        self.cam_view = None
        self.dispenser_view = None
        self.frameData = None
        self.centermarked = None

        self.cnc_shouldinitialize = None
        self.message = []

        #Launch GuiThread - helps to manage some types of events
        #self.guiThread = GuiThread(cam=self.cam,
        #                            cnc=self.cnc,
        #                            opto=self.opto,
        #                            dispenser=self.dispenser,
        #                            stim=self.stim,
        #                            ui=self.ui,
        #                            trial=self.trial)
        #self.guiThread.start()

        # Setup cnc buttons
        self.ui.cnc_start_button.clicked.connect(lambda x: self.trackerStart())
        self.ui.cnc_stop_button.clicked.connect(lambda x: self.trackerStop())
        self.ui.cnc_initialize_button.clicked.connect(lambda x: self.tracker.cnc_shouldinitialize.set())
        self.ui.cnc_move_center_button.clicked.connect(lambda x: self.tracker.start_moving_to_center())
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

        # Setup dispenser buttons
        self.ui.dispenser_start_button.clicked.connect(lambda x: self.dispenserStart())
        self.ui.dispenser_stop_button.clicked.connect(lambda x: self.dispenserStop())
        self.ui.open_gate_button.clicked.connect(lambda x: self.openDispenser())
        self.ui.close_gate_button.clicked.connect(lambda x: self.closeDispenser())
        self.ui.calibrate_gate_button.clicked.connect(lambda x: self.calibrateDispenser())
        self.ui.close_gate_button.setEnabled(False)
        self.ui.open_gate_button.setEnabled(False)
        self.ui.calibrate_gate_button.setEnabled(False)

        # Setup opto buttons
        self.ui.opto_start_button.clicked.connect(lambda x: self.optoStart())
        self.ui.opto_stop_button.clicked.connect(lambda x: self.optoStop())
        self.ui.opto_on_button.clicked.connect(lambda x: self.opto.on())
        self.ui.opto_off_button.clicked.connect(lambda x: self.opto.off())
        self.ui.opto_pulse_button.clicked.connect(lambda x: self.opto.pulse())
        self.ui.opto_foraging_button.clicked.connect(lambda x: self.foraging())
        self.ui.opto_foraging_button.setEnabled(False)
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

        # Setup camera sliders
        self.ui.thresh_slider.setValue(200)
        self.ui.thresh_label.setText(str(self.ui.thresh_slider.value()))
        self.ui.r_min_slider.setValue(2)
        self.ui.r_min_label.setText(str(self.ui.r_min_slider.value()))
        self.ui.r_max_slider.setValue(8)
        self.ui.r_max_label.setText(str(self.ui.r_max_slider.value()))
        self.ui.loop_gain_slider.setValue(80)
        self.ui.loop_gain_label.setText(str(self.ui.loop_gain_slider.value()))
        self.ui.thresh_slider.valueChanged.connect(self.thresholdChange)
        self.ui.r_min_slider.valueChanged.connect(self.rminChange)
        self.ui.r_max_slider.valueChanged.connect(self.rmaxChange)
        self.ui.loop_gain_slider.valueChanged.connect(self.loopgainChange)

        # Setup camera checkboxes
        #self.ui.image_type_combo.setEnabled(False)
        #self.ui.image_type_combo.activated[str].connect(self.image_type)
        self.ui.draw_contours_checkbox.setChecked(True)
        self.ui.draw_contours_checkbox.setEnabled(False)
        self.ui.show_threshold_checkbox.setChecked(False)
        self.ui.show_threshold_checkbox.setEnabled(False)
        self.ui.show_threshold_checkbox.stateChanged.connect(lambda x: self.camThreshold())
        self.ui.draw_contours_checkbox.stateChanged.connect(lambda x: self.camContours())

        # Setup metadata input
        self.ui.save_metadata_button.clicked.connect(partial(self.saveMetadata, self.ui))

        # Setup visual stimuli buttons
        self.ui.stim_start_button.clicked.connect(lambda x: self.stimStart())
        self.ui.stim_per_trial_button.clicked.connect(lambda x: self.stimPerTrial())
        self.ui.stim_within_trial_button.clicked.connect(lambda x: self.stimWithinTrial())
        self.ui.stim_per_trial_button.setEnabled(False)
        self.ui.stim_within_trial_button.setEnabled(False)

    @property
    def cnc(self):
        try:
            return self.tracker.cnc
        except:
            return None

    @property
    def cncinit(self):
        try:
            return self.tracker.is_init
        except:
            return False

    @property
    def cam(self):
        return self._cam

    @cam.setter
    def cam(self, value):
        self._cam = value
        try:
            self.tracker.camThread = value
        except:
            pass

    def camThreshold(self):
        if self.cam is not None:
            if self.ui.show_threshold_checkbox.isChecked():
                self.cam.show_threshold = True
            else:
                self.cam.show_threshold = False

    def camContours(self):
        if self.cam is not None:
            if self.ui.draw_contours_checkbox.isChecked():
                self.cam.draw_contours = True
            else:
                self.cam.draw_contours = False

    def stimPerTrial(self):
        self.stim.mode = 'random_stim'

    def stimWithinTrial(self):
        self.stim.mode = 'random_direction'
        self.stim.pause_duration = 2.0
        self.stim.stim_duration = 2.0

    def stimStart(self):
        self.stim = StimThread()
        self.ui.stim_stop_button.setEnabled(True)
        self.ui.stim_start_button.setEnabled(False)
        self.ui.stim_per_trial_button.setEnabled(True)
        self.ui.stim_within_trial_button.setEnabled(True)
        
    def saveMetadata(self):
        age = self.age_textbox.toPlainText()
        timezone = self.timezone_textbox.toPlainText()
        genotype = self.genotype_textbox.toPlainText()
        #with open('somefile.txt', 'a') as f:
        #    f.write(mytext)

    def thresholdChange(self):
        value = self.ui.thresh_slider.value()
        self.ui.thresh_label.setText(str(value))
        self.cam.threshold = value

    def rminChange(self):
        value = self.ui.r_min_slider.value()
        self.ui.r_min_label.setText(str(value))
        self.cam.cam.r_min = value

    def rmaxChange(self):
        value = self.ui.r_max_slider.value()
        self.ui.r_max_label.setText(str(value))
        self.cam.cam.r_max = value

    def loopgainChange(self):
        value = self.ui.loop_gain_slider.value()
        self.ui.loop_gain_label.setText(str(value))
        self.tracker.a = value

    def dispenserStart(self):
        self.dispenser = FlyDispenser()
        self.dispenser.start()
        self.dispenser_view = DispenserView(self.dispenser)
        self.ui.dispenser_start_button.setEnabled(False)
        self.ui.dispenser_stop_button.setEnabled(True)
        self.ui.close_gate_button.setEnabled(True)
        self.ui.open_gate_button.setEnabled(True)
        self.ui.calibrate_gate_button.setEnabled(True)

    def dispenserStop(self):
        self.dispenser_view.close()
        self.dispenser.stop()
        self.dispenser = None
        self.ui.dispenser_start_button.setEnabled(True)
        self.ui.dispenser_stop_button.setEnabled(False)
        self.ui.close_gate_button.setEnabled(False)
        self.ui.open_gate_button.setEnabled(False)
        self.ui.calibrate_gate_button.setEnabled(False)

    def openDispenser(self):
        self.dispenser.open_gate()

    def closeDispenser(self):
        self.dispenser.close_gate()

    def calibrateDispenser(self):
        self.dispenser.calibrate_gate()

    def trackerStart(self):
        # find if we should initialize
        mail = Mail()
        CncPopup(mail)
        cnc_shouldinitialize = mail.message

        # start tracker
        self.tracker = TrackThread(camThread=self.cam)

        if cnc_shouldinitialize:
            self.tracker.cnc_shouldinitialize.set()

        self.tracker.start()

        # set status of UI buttons
        self.ui.cnc_up_button.setEnabled(True)
        self.ui.cnc_down_button.setEnabled(True)
        self.ui.cnc_left_button.setEnabled(True)
        self.ui.cnc_right_button.setEnabled(True)
        self.ui.cnc_start_button.setEnabled(False)
        self.ui.cnc_stop_button.setEnabled(True)
        self.ui.cnc_initialize_button.setEnabled(True)
        self.ui.cnc_move_center_button.setEnabled(True)
        self.ui.cnc_mark_center_button.setEnabled(True)

    def trackerStop(self):
        self.tracker.stop()
        self.tracker = None

        # set status of UI buttons
        self.ui.cnc_up_button.setEnabled(False)
        self.ui.cnc_down_button.setEnabled(False)
        self.ui.cnc_left_button.setEnabled(False)
        self.ui.cnc_right_button.setEnabled(False)
        self.ui.cnc_start_button.setEnabled(True)
        self.ui.cnc_stop_button.setEnabled(False)
        self.ui.cnc_initialize_button.setEnabled(False)
        self.ui.cnc_move_center_button.setEnabled(False)
        self.ui.cnc_mark_center_button.setEnabled(False)

    def markCenter(self):
        self.tracker.mark_center()
        self.centermarked = True

    def camStart(self):
        self.cam = CamThread()
        self.cam.start()
        self.cam_view = CameraView(self.cam)

        self.ui.camera_start_button.setEnabled(False)
        self.ui.camera_stop_button.setEnabled(True)
        self.ui.draw_contours_checkbox.setEnabled(True)
        self.ui.show_threshold_checkbox.setEnabled(True)

    def camStop(self):
        self.cam_view.close()

        self.cam.stop()
        self.cam = None

        self.ui.draw_contours_checkbox.setChecked(True)
        self.ui.show_threshold_checkbox.setChecked(False)
        self.ui.camera_start_button.setEnabled(True)
        self.ui.camera_stop_button.setEnabled(False)
        self.ui.draw_contours_checkbox.setEnabled(False)
        self.ui.show_threshold_checkbox.setEnabled(False)

    def optoStart(self):
        self.opto = OptoThread(cncThread=self.tracker.cncThread, camThread=self.cam,
                               trackThread=self.tracker, trialThread = self.trial)
        self.opto.start()
        self.ui.opto_start_button.setEnabled(False)
        self.ui.opto_stop_button.setEnabled(True)
        self.ui.opto_on_button.setEnabled(True)
        self.ui.opto_off_button.setEnabled(True)
        self.ui.opto_pulse_button.setEnabled(True)
        self.ui.opto_foraging_button.setEnabled(True)

    def optoStop(self):
        self.opto.off()
        self.opto.stop()
        self.opto = None
        self.ui.opto_start_button.setEnabled(True)
        self.ui.opto_stop_button.setEnabled(False)
        self.ui.opto_on_button.setEnabled(False)
        self.ui.opto_off_button.setEnabled(False)
        self.ui.opto_pulse_button.setEnabled(False)
        self.ui.opto_foraging_button.setEnabled(False)

    def foraging(self):
        self.opto.foraging = True

    def experimentStart(self):
        if self.cam is None:
            self.message.append("Turn on the camera before starting the experiment.")
        if self.tracker is None:
            self.message.append("Turn on the cnc before starting the experiment.")
        if not self.cncinit:
            if not self.centermarked:
                self.message.append("Initialize cnc or mark center before starting the experiment.")
        if self.message:
            print(self.message)
            MessagePopup(self.message)
            self.message = []
        else:
            self.trial = TrialThread(cam=self.cam, dispenser=self.dispenser, tracker=self.tracker,
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
        self.trial = None
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

    #def keyPressEvent(self, e):    
    #    if e.key() == Qt.Key_Escape:
    #        self.close()

    def shutdown(self, app):
        app.exec_()
        if self.opto is not None:
            self.opto.off()
            self.opto.stop()
        if self.cam_view is not None:
            self.cam_view.close()
        if self.cam is not None:
            self.cam.stop()
        if self.tracker is not None:
            self.tracker.stop()
        if self.trial is not None:
            self.trial._stop_trial()
            self.trial.stop()
        if self.dispenser_view is not None:
            self.dispenser_view.close()
        if self.dispenser is not None:
            self.dispenser.stop()
        print('Shutdown Called')

    # class GateState(QWidget):
    #     valueChanged = pyqtSignal(object)

    #     def __init__(self, parent=None):
    #         super(GateState, self).__init__(parent)
    #         self._t = self.dispenser.gate_state

    #     @property
    #     def t(self):
    #         return self._t

    #     @t.setter
    #     def t(self, value):
    #         self._t = value
    #         self.valueChanged.emit(value)

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

# ref: https://github.com/bsdnoobz/opencv-code/blob/master/opencv-qt-integration-1/python/ImageViewer.py
class CameraView(QWidget):
    def __init__(self, cam, fps=24):
        super().__init__()
        self.title = 'Camera View'
        self.left = 794
        self.top = 23
        self.width = 659
        self.height = 496

        self.cam = cam

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_window)
        self.timer.start(int(1/fps*1000))

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.image_label = QtWidgets.QLabel()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.image_label)
        self.setLayout(self.main_layout)

        self.show()

    def update_window(self):
        try:
            img = self.cam.outFrame
        except:
            return

        if img is not None:
            height, width, bytesPerComponent = img.shape
            bytesPerLine = 3 * width
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
            q_img = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap)

    def close(self):
        self.timer.stop()
        super().close()

class DispenserView(QWidget):
    def __init__(self, dispenser, fps=24):
        super().__init__()
        self.title = 'Dispenser View'
        self.left = 794
        self.top = 562
        self.width = 300
        self.height = 300

        self.dispenser = dispenser
        self.plot_data = np.zeros((128, 128))

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_window)
        self.timer.start(int(1/fps*1000))

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.image_label = QtWidgets.QLabel()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.image_label)
        self.setLayout(self.main_layout)

        self.show()

    def update_window(self):
        if self.dispenser.display_frame is not None:
            self.plot_data = np.roll(self.plot_data, 1, 0)
            self.plot_data[0] = self.dispenser.display_frame
            self.plot_data = self.plot_data.astype(np.uint8)
        img = QtGui.QImage(self.plot_data, self.plot_data.shape[0], self.plot_data.shape[1], QtGui.QImage.Format_Indexed8)
        pixmap = QtGui.QPixmap.fromImage(img)
        pixmap = pixmap.scaledToWidth(300)
        self.image_label.setPixmap(pixmap)

    def close(self):
        self.timer.stop()
        super().close()
#
def main():
    app = QApplication(sys.argv)
    dialog = QtWidgets.QMainWindow()
    prog = MainGui(dialog)
    #sys.exit(app.exec_())
    sys.exit(prog.shutdown(app))

if __name__ == '__main__':
    main()