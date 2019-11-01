#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

import json
from flystim.stim_server import launch_stim_server
from time import time

from random import choice
from math import pi

from flystim.screen import Screen
from flyrpc.multicall import MyMultiCall
from flystim.trajectory import RectangleTrajectory

from time import sleep

import numpy as np

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
        fullscreen = True
    elif dir.lower() in ['n', 'north']:
        id = 3
        rotation = 0
        offset = (0, w/2, h/2)
        fullscreen = True
    elif dir.lower() in ['s', 'south']:
        id = 2
        rotation = pi
        offset = (0, -w/2, h/2)
        fullscreen = True
    elif dir.lower() in ['e', 'east']:
        id = 4
        rotation = -pi/2
        offset = (w/2, 0, h/2)
        fullscreen = True
    elif dir.lower() == 'gui':
        id = 0
        rotation = 0
        offset = (0, w/2, h/2)
        fullscreen = False
    else:
        raise ValueError('Invalid direction.')

    return Screen(id=id, server_number=1, rotation=rotation, width=w, height=h, offset=offset, fullscreen=fullscreen,
                  name='BigRig {} Screen'.format(dir.title()))

class StimThread:
    def __init__(self, angle_change_thresh=3):
        screens = [get_bigrig_screen(dir) for dir in ['n', 'e', 's', 'w', 'gui']]
        self.manager = launch_stim_server(screens)
        self.manager.hide_corner_square()

        self.pause_duration = None
        self.stim_duration = None

        self.mode = None
        self.stim_loaded = False
        self.stim_state = {}

        self.closed_loop_pos = False
        self.closed_loop_angle = False

        self.angle_change_thresh = angle_change_thresh
        self.last_angle = 0

    def get_random_direction(self):
        return choice([-400, -200, -100, -20, 20, 100, 200, 400])

    def get_random_stim(self):
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
        return kwargs

    def updateStim(self, trial_dir, fly_pos_x, fly_pos_y, fly_angle):
        if self.manager is None:
            return

        if not self.stim_loaded:
            return

        # send fly position and orientation to stimulus
        multicall = MyMultiCall(self.manager)

        if self.closed_loop_pos:
            if fly_pos_x is not None and fly_pos_y is not None:
                multicall.set_global_fly_pos(fly_pos_x, fly_pos_y, 0)
        else:
            multicall.set_global_fly_pos(0, 0, 0)

        if self.closed_loop_angle:
            if fly_angle is not None:
                if abs(fly_angle-self.last_angle) > self.angle_change_thresh:
                    multicall.set_global_theta_offset(fly_angle)
                    self.last_angle = fly_angle
        else:
            multicall.set_global_theta_offset(0)

        if len(multicall.request_list) > 0:
            multicall()

        if self.mode == 'multi_rotation':
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
        elif self.mode == 'single_stim':
            pass
        elif self.mode == 'multi_stim':
            t = time()
            if (t - self.stim_state['last_update']) > self.stim_duration:
                kwargs = self.get_random_stim()
                #self.manager.update_stim(**kwargs)
                self.manager.load_stim(**kwargs)
                self.manager.start_stim()
                self.log_to_dir('UpdateStim: {}'.format(pretty_json(kwargs)), trial_dir)

                self.stim_state['last_update'] = t
        elif self.mode == 'minseung':
            pass
        elif self.mode == 'avery':
            pass
        else:
            raise Exception('Invalid MrStim mode.')

    def stopStim(self, trial_dir):
        if self.manager is None:
            return

        self.manager.stop_stim()
        self.stim_loaded = False

        self.log_to_dir('StopStim', trial_dir)

    def nextTrial(self, trial_dir): #was nextStim
        if self.manager is None:
            return

        if self.mode == 'single_stim':
            #kwargs = self.get_random_stim()
            trajectory = RectangleTrajectory(x=0, y=90, angle=0, w=3, h=180)
            kwargs = {'name': 'MovingPatch', 'trajectory': trajectory.to_dict()}
            self.stim_state = {}

        elif self.mode == 'multi_stim':
            kwargs = self.get_random_stim()
            self.stim_state = {'last_update': time()}

        elif self.mode == 'multi_rotation':
            rate = self.get_random_direction()
            kwargs = {'name': 'SineGrating', 'angle': 0, 'period': 20, 'rate': rate, 'color': 1.0, 'background': 0.0}
            self.stim_state = {'last_update': time(), 'paused': False}

        elif self.mode == 'avery':
            kwargs = {'name': 'RandomBars', 'period': 90, 'vert_extent': 180, 'width': 10, 'rand_min': 0.0,\
                      'rand_max': 0.0, 'start_seed': 0, 'update_rate': 0.0, 'background': 0.5, 'rgb': (0.0, 1.0, 0.0)}

        elif self.mode == 'loom':

            rv_ratio = 0.040  # seconds (try these values r/v values of 10, 40, 70, 100 and 140 ms)
            stim_time = 1  # seconds

            end_size = 60  # deg
            start_size = 1

            time_steps = np.arange(0, stim_time - 0.001, 0.001)  # time steps of trajectory
            # calculate angular size at each time step for this rv ratio
            angular_size = 2 * np.rad2deg(np.arctan(rv_ratio * (1 / (stim_time - time_steps))))

            ## shift curve vertically so it starts at start_size
            min_size = angular_size[0]
            size_adjust = min_size - start_size
            angular_size = angular_size - size_adjust
            ## Cap the curve at end_size and have it just hang there

            max_size_ind = np.where(angular_size > end_size)[0][0]
            angular_size[max_size_ind:] = end_size

            def main():

                num_trials = 1

                manager = launch_stim_server(Screen(fullscreen=False))

                trajectory = RectangleTrajectory(w=list(zip(time_steps, angular_size)),

                                                 h=list(zip(time_steps, angular_size)),

                                                 x=90,

                                                 y=90,

                                                 color=0)

                for _ in range(num_trials):
                    manager.load_stim(name='MovingPatch', trajectory=trajectory.to_dict(), background=0.5)

            # trajectory = RectangleTrajectory(h=[(0,10),(.5,50),(1,10),(1.5,50),(2,10),(2.5,50),(3,10),(3.5,50)],
            #                          w=[(0,10),(.5,50),(1,10),(1.5,50),(2,10),(2.5,50),(3,10),(3.5,50)],
            #                          x=[(0,0),(.5,0),(1,90),(1.5,90),(2,180),(2.5,180),(3,270),(3.5,270)],
            #                          y=[(0,45),(.5,45),(1,45),(1.5,45),(2,45),(2.5,45),(3,45),(3.5,45)],
            #                          color=0
            #                         )
            # kwargs = {'name': 'MovingPatch', 'background': 0.5, 'trajectory': trajectory}


        else:
            raise Exception('Invalid Stim mode.')

        print('Moving to next trial stimuli.')

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