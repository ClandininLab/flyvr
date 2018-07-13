import sys
import types
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from PyQt5.QtCore import QBasicTimer
from functools import partial

def valuechg(ui, data):
    ui.thresh_label.setText(str(data))

app = QApplication(sys.argv)

ui = uic.loadUi('main.ui')
ui.show()
ui.thresh_slider.valueChanged.connect(partial(valuechg, ui))
ui.thresh_slider.setValue(99)
sys.exit(app.exec_())

