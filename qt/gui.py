from time import time, sleep
from flyvr.service import Service

class GuiThread(Service):
    def __init__(self, cam, cnc, opto, dispenser, stim, ui, trial):
        self.cam = cam
        self.cnc = cnc
        self.opto = opto
        self.dispenser = dispenser
        self.stim = stim
        self.ui = ui
        self.trial = trial

        # call constructor from parent
        super().__init__()

    # overriding method from parent...
    def loopBody(self):
        sleep(0.1)
        # Handle display of fly parameters
        if self.cam is not None:
            if self.cam.flyData is not None:
                if self.cam.flyData.MA is not None:
                    self.ui.fly_major_axis_label.setText(str(self.cam.flyData.MA))
                else:
                    self.ui.fly_major_axis_label.setText('N/A')

                if self.cam.flyData.ma is not None:
                    self.ui.fly_minor_axis_label.setText(str(self.cam.flyData.ma))
                else:
                    self.ui.fly_minor_axis_label.setText('N/A')

                if self.cam.flyData.MA is not None:
                    self.ui.fly_aspect_ratio_label.setText(str(self.cam.flyData.MA / self.cam.flyData.ma))
                else:
                    self.ui.fly_aspect_ratio_label.setText('N/A')

        # Handle bigrig state
        if self.trial is not None:
            self.ui.bigrig_state_label.setText(self.trial.state)

        # Handle experiment and trial display
        if self.trial is not None:
            self.ui.experiment_label.setText(str(self.trial.exp))
        else:
            self.ui.experiment_label.setText('N/A')

        if self.trial is not None:
            self.ui.trial_label.setText(str(self.trial.trial_count))
        else:
            self.ui.trial_label.setText('N/A')

        # Handle gate close/open buttons
        if self.dispenser is not None:
            if self.dispenser.gate_state == 'open':
                self.ui.open_gate_button.setEnabled(False)
                self.ui.close_gate_button.setEnabled(True)
            elif self.dispenser.gate_state == 'close':
                self.ui.open_gate_button.setEnabled(True)
                self.ui.close_gate_button.setEnabled(False)

        # Handle trial duration
        if self.trial is not None:
            if self.trial is not None:
                trial_duration = self.trial.trial_start_t - time()
        else:
            trial_duration = 0
        self.ui.trial_duration_label.setText(str(int(trial_duration)))

        # Handle stim label
        if self.stim is not None:
            self.ui.current_stim_label.setText(str(self.stim.stim_type))
        else:
            self.ui.current_stim_label.setText('N/A')

        # Handle green and red lights
        #print(self.cnc)
        if self.cnc is None:
            self.ui.cnc_red_light.show()
        else:
            print("trying to hide")
            self.ui.cnc_red_light.hide()