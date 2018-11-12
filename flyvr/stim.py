#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

import json
from flystim.stim_server import launch_stim_server
from time import time

from random import choice
from math import pi

from flystim.screen import Screen

import os, os.path

def pretty_json(d):
    return json.dumps(d, indent=2, sort_keys=True)

def get_bigrig_screen(dir):
    w = 43 * 2.54e-2
    h = 24 * 2.54e-2

    if dir.lower() in ['w', 'west']:
        id = 1
        rotation = pi/2
        offset = (-w/2, 0, h/2)
    elif dir.lower() in ['n', 'north']:
        id = 2
        rotation = 0
        offset = (0, w/2, h/2)
    elif dir.lower() in ['s', 'south']:
        id = 3
        rotation = pi
        offset = (0, -w/2, h/2)
    elif dir.lower() in ['e', 'east']:
        id = 4
        rotation = -pi/2
        offset = (w/2, 0, h/2)
    elif dir.lower() == 'gui':
        id = 0
        rotation = 0
        offset = (0, w/2, h/2)
    else:
        raise ValueError('Invalid direction.')

    return Screen(id=id, server_number=1, rotation=rotation, width=w, height=h, offset=offset,
                  name='BigRig {} Screen'.format(dir.title()))

class StimThread:
    def __init__(self):
        screens = [get_bigrig_screen(dir) for dir in ['n', 'e', 's', 'w', 'gui']]
        self.manager = launch_stim_server(screens)
        self.manager.hide_corner_square()

        self.pause_duration = None
        self.stim_duration = None

        self.mode = None
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
            stim_type = choice(['SineGrating', 'SineGrating', 'Dark', 'Bright', 'Grey', 'RandomCheckerboard'])
            if stim_type is 'SineGrating':
                angle = choice([0, 90])
                kwargs = {'name': 'SineGrating', 'angle': angle, 'period': 20, 'rate': 0, 'color': 1.0,
                          'background': 0.0}
            elif stim_type is 'Grey':
                kwargs = {'name': 'ConstantBackground', 'background': 0.5}
            elif stim_type is 'Dark':
                kwargs = {'name': 'ConstantBackground', 'background': 0.0}
            elif stim_type is 'Bright':
                kwargs = {'name': 'ConstantBackground', 'background': 1.0}
            elif stim_type is 'RandomCheckerboard':
                kwargs = {'name': 'RandomGrid', 'update_rate': 0}
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

if __name__ == '__main__':
    main()