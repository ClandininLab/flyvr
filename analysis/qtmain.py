import sys
import numpy as np

from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from functools import partial
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui

from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtCore import QDir, Qt, QUrl

def main():
    def valuechg(ui, data):
        ui.thresh_label.setText(str(data))

    app = QApplication(sys.argv)

    ui = uic.loadUi('main.ui')

    ui.show()

    ui.thresh_slider.valueChanged.connect(partial(valuechg, ui))
    ui.thresh_slider.setValue(99)

    videofile = '/Users/lukebrezovec/FlyTracker/Data/trial-4-20180919-182832/cam_compr.mkv'
    #videofile = '/Users/lukebrezovec/FlyTracker/Data/exp-20180111-185730-leg-video-2x/trial-1-20180111-185824-8ms/converted_quicktime_s.mov'
    ui.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
    ui.play_button.clicked.connect(lambda x: play_movie(ui))

    ui.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(videofile)))
    ui.mediaPlayer.setVideoOutput(ui.video_window)
    ui.play_button.setEnabled(True)

    file = '/Volumes/groups/trc/data/Brezovec/VR Arena/exp-20181104-162518/raw_gate_data.txt'
    data = np.genfromtxt(file, max_rows=100)
    #data = np.transpose(data)
    #data.astype(np.int8)
    #print(np.dtype(data))
    #data = np.random.random(10000)
    #data = data.reshape(100,100)
    #data = data.astype(int)
    print(data)
    QI=QtGui.QImage(data, data.shape[0], data.shape[1], QtGui.QImage.Format_Indexed8)
    ui.test_label.setPixmap(QPixmap.fromImage(QI))

    #dispenser = launch_server(flyvr.gate_control)
    #ui.start_trial_button.clicked.connect(lambda x: dispenser.release_fly())
    #ui.open_gate_button.clicked.connect(lambda x: dispenser.open_gate())
    #ui.close_gate_button.clicked.connect(lambda x: dispenser.close_gate())

    #opto = OptoService()
    #ui.opto_on_button.clicked.connect(lambda x: opto.on())
    #ui.opto_off_button.clicked.connect(lambda x: opto.off())
    #ui.opto_pulse_button.clicked.connect(lambda x: opto.pulse())

    sys.exit(app.exec_())

def play_movie(ui):
    if ui.mediaPlayer.state() == QMediaPlayer.PlayingState:
        ui.mediaPlayer.pause()
    else:
        ui.mediaPlayer.play()

if __name__ == '__main__':
    main()

