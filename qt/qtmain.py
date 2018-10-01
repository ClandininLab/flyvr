import sys
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from functools import partial

import flyvr.gate_control
from flyrpc.launch import launch_server

def main():
    def valuechg(ui, data):
        ui.thresh_label.setText(str(data))

    app = QApplication(sys.argv)

    ui = uic.loadUi('main.ui')

    ui.show()

    ui.thresh_slider.valueChanged.connect(partial(valuechg, ui))
    ui.thresh_slider.setValue(99)

    client = launch_server(flyvr.gate_control)
    releaseFly = client.releaseFly
    ui.start_trial_button.clicked.connect(lambda x: releaseFly())

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

