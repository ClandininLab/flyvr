import sys
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
from functools import partial

import flyvr.gate_control
from flyvr.opto import OptoService
from flyrpc.launch import launch_server

def main():
    def valuechg(ui, data):
        ui.thresh_label.setText(str(data))

    app = QApplication(sys.argv)

    ui = uic.loadUi('main.ui')

    ui.show()

    ui.thresh_slider.valueChanged.connect(partial(valuechg, ui))
    ui.thresh_slider.setValue(99)

    dispenser = launch_server(flyvr.gate_control)
    ui.start_trial_button.clicked.connect(lambda x: dispenser.release_fly())
    ui.open_gate_button.clicked.connect(lambda x: dispenser.open_gate())
    ui.close_gate_button.clicked.connect(lambda x: dispenser.close_gate())

    opto = OptoService()
    ui.opto_on_button.clicked.connect(lambda x: opto.on())
    ui.opto_off_button.clicked.connect(lambda x: opto.off())
    ui.opto_pulse_button.clicked.connect(lambda x: opto.pulse())

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

