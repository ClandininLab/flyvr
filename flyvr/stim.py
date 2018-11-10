#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

from flyrpc.launch import launch_server
import json
import flystim.stim_server
from time import time

from random import choice
import os, os.path

def pretty_json(d):
    return json.dumps(d, indent=2, sort_keys=True)

class StimThread:
    def __init__(self, mode='random_direction', pause_duration=2.0, stim_duration=2.0, use_stimuli=False):
        try:
            assert use_stimuli
            self.manager = launch_server(flystim.stim_server, setup_name='bigrig')
            self.manager.hide_corner_square()
        except:
            print('Not using visual stimulus.')
            self.manager = None

        self.pause_duration = pause_duration
        self.stim_duration = stim_duration

        self.mode = mode
        self.stim_loaded = False
        self.stim_state = {}

    def get_random_direction(self):
        return choice([-100, -20, 20, 100])

    def updateStim(self, trial_dir):
        if self.manager is None:
            return

        if not self.stim_loaded:
            return

        if self.mode == 'random_direction':
            t = time()

            if self.stim_state['paused']:
                if (t-self.stim_state['last_update']) > self.pause_duration:
                    rate = self.get_random_direction()
                    kwargs = {'rate': rate}
                    self.manager.update_stim(**kwargs)
                    self.manager.start_stim()
                    self.log_to_dir('UpdateStim: {}'.format(pretty_json(kwargs)), trial_dir)

                    self.stim_state['last_update'] = t
                    self.stim_state['paused'] = False
            elif (t-self.stim_state['last_update']) > self.stim_duration:
                self.manager.pause_stim()
                self.log_to_dir('PauseStim', trial_dir)
                self.stim_state['last_update'] = t
                self.stim_state['paused'] = True
        elif self.mode == 'random_stim':
            pass
        else:
            raise Exception('Invalid MrStim mode.')

    def stopStim(self, trial_dir):
        if self.manager is None:
            return

        self.manager.stop_stim()
        self.stim_loaded = False

        self.log_to_dir('StopStim', trial_dir)

    def nextStim(self, trial_dir):
        if self.manager is None:
            return

        if self.mode == 'random_stim':
            stim_type = choice(['SineGrating', 'SineGrating', 'Grey', 'Dark'])
            if stim_type is 'SineGrating':
                angle = choice([0, 90])
                kwargs = {'name': 'SineGrating', 'angle': angle, 'period': 20, 'rate': 0, 'color': 1.0,
                          'background': 0.0}
            elif stim_type is 'Grey':
                kwargs = {'name': 'ConstantBackground', 'background': 0.5}
            elif stim_type is 'Dark':
                kwargs = {'name': 'ConstantBackground', 'background': 0.0}
            else:
                raise Exception('Invalid stimulus type.')

            self.stim_state = {}
        elif self.mode == 'random_direction':
            rate = self.get_random_direction()
            kwargs = {'name': 'SineGrating', 'angle': 0, 'period': 20, 'rate': rate, 'color': 1.0, 'background': 0.0}
            self.stim_state = {'last_update': time(), 'paused': False}
        else:
            raise Exception('Invalid MrStim mode.')

        print('Moving to next stimulus.')

        self.manager.load_stim(**kwargs)
        self.manager.start_stim()
        self.stim_loaded = True

        self.log_to_dir('NewStim: {}'.format(pretty_json(kwargs)), trial_dir)

    def log_to_dir(self, text, dir):
        if dir is None:
            return

        stimuli_file_name = os.path.join(dir, 'stimuli.txt')

        file_mode = 'a' if os.path.isfile(stimuli_file_name) else 'w'
        self.stimuli_file = open(stimuli_file_name, file_mode)

        self.stimuli_file.write('@{} {}\n'.format(time(), text))

        self.stimuli_file.flush()
        self.stimuli_file.close()

        print('stimuli logged.')

def main():
    MrDisplay()

if __name__ == '__main__':
    main()
