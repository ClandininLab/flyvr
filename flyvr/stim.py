#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

import json
from flystim.stim_server import launch_stim_server
from time import time

from random import choice
from math import pi

from flystim.screen import Screen
from flyrpc.multicall import MyMultiCall
from flystim.trajectory import Trajectory

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

        # set idle background between trials
        self.manager.set_idle_background(0.0)

        self.mode = None
        self.stim_loaded = False
        self.stim_state = {}
        self.stim_state['paused'] = True
        t = time()
        self.stim_state['last_update'] = t
        self.count_stim = 0

        self.closed_loop_pos = False
        self.closed_loop_angle = False

        self.angle_change_thresh = angle_change_thresh
        self.last_angle = 0
        self.present_angle = 0

    def get_random_direction(self):
        return choice([-400, -200, -100, -20, 20, 100, 200, 400])

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
                    self.kwargs = {'rate': rate}
                    self.manager.update_stim(**self.kwargs)
                    self.manager.start_stim()
                    self.log_to_dir('UpdateStim: {}'.format(pretty_json(self.kwargs)), trial_dir)

                    self.stim_state['last_update'] = t
                    self.stim_state['paused'] = False
            elif (t-self.stim_state['last_update']) > self.stim_duration:
                self.manager.pause_stim()
                self.log_to_dir('PauseStim', trial_dir)
                self.stim_state['last_update'] = t
                self.stim_state['paused'] = True
        elif self.mode == 'corner_bars':
            pass

        elif self.mode == 'loom':
            t = time()
            if fly_angle is not None:
                self.present_angle = fly_angle - 90.0  # for offset
            if self.count_stim <= 1:
                #print('in pre-stim stim')
                self.pause_duration = 1  # This is the initial delay
            elif self.count_stim > 1:
                self.pause_duration = 4  # this is the interstim interval

            if self.stim_state['paused']:
                if (t-self.stim_state['last_update'])>self.pause_duration:
                    print('loom in loop')
                    print('fly angle', fly_angle)
                    print('show angle', self.present_angle)

                    self.kwargs['theta'] = self.present_angle

                    self.manager.load_stim(**self.background_kwargs)
                    self.manager.load_stim(**self.kwargs)
                    self.manager.start_stim()
                    self.count_stim = self.count_stim + 1
                    self.log_to_dir('UpdateStim: {}'.format(pretty_json(self.kwargs)), trial_dir)
                    self.stim_state['last_update'] = t
                    self.stim_state['paused'] = False
            elif (t - self.stim_state['last_update']) > self.stim_time:
                self.manager.stop_stim()
                self.log_to_dir('PauseStim', trial_dir)
                self.stim_state['last_update'] = t
                self.stim_state['paused'] = True

        else:
            raise Exception('Invalid Stim mode.')

    def stopStim(self, trial_dir):
        if self.manager is None:
            return

        self.manager.stop_stim()
        self.stim_loaded = False

        self.log_to_dir('StopStim', trial_dir)

    def nextTrial(self, trial_dir): #was nextStim
        print('Mode = {}'.format(self.mode))
        if self.manager is None:
            return

        if self.mode == 'multi_rotation':
            rate = self.get_random_direction()
            self.kwargs = {'name': 'SineGrating', 'angle': 0, 'period': 20, 'rate': rate, 'color': 1.0, 'background': 0.0}
            self.stim_state = {'last_update': time(), 'paused': False}

        elif self.mode == 'rotating_bars':
            self.kwargs = {'name': 'RotatingGrating', 'rate': 30, 'period': 20, 'mean': 0.5, 'contrast': 1.0, \
                      'profile': 'square', 'color': [0, 0, 1, 1]}

        elif self.mode == 'corner_bars':

             distribution_data = {'name': 'Binary',
                                  'args':[],
                                  'kwargs':{'rand_min':0.0, 'rand_max':0.0}}

             self.kwargs = {'name': 'RandomBars', 'period': 90, 'vert_extent': 170, 'width': 10, \
                       'distribution_data':distribution_data, 'start_seed': 0, 'update_rate': 0.0, \
                       'background': 1.0, 'color': [0.0, 0.0, 1.0, 1.0], 'theta_offset': 46}

        elif self.mode == 'loom':
            self.manager.set_idle_background(0.5)
            self.stim_time = 3
            start_size = 2 # radius, degrees
            end_size = 30
            rv_ratio = 20 / 1e3  # msec -> sec
            time_steps, angular_size = getLoomTrajectory(rv_ratio, self.stim_time, start_size, end_size)

            r_traj = Trajectory(list(zip(time_steps, angular_size)), kind='previous').to_dict()

            self.background_kwargs = {'name':'ConstantBackground', 'color':[0.5, 0.5, 0.5, 1.0], 'side_length':100}
            self.manager.load_stim(**self.background_kwargs)

            self.kwargs = {'name':'MovingSpot', 'radius':r_traj, 'phi':-30.0, 'theta':0.0, 'color':0.0, 'hold':True}

        else:
            raise Exception('Invalid Stim mode.')

        print('Moving to next trial stimuli.')


        self.manager.load_stim(**self.kwargs)
        self.stim_loaded = True
        self.manager.start_stim()
        self.log_to_dir('NewStim: {}'.format(pretty_json(self.kwargs)), trial_dir)



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

def getLoomTrajectory(rv_ratio, stim_time, start_size, end_size):
    # rv_ratio in sec
    time_steps = np.arange(0, stim_time-0.001, 0.001)  # time steps of trajectory
    # calculate angular size at each time step for this rv ratio
    angular_size = 2 * np.rad2deg(np.arctan(rv_ratio * (1 / (stim_time - time_steps))))

    # shift curve vertically so it starts at start_size
    min_size = angular_size[0]
    size_adjust = min_size - start_size
    angular_size = angular_size - size_adjust
    # Cap the curve at end_size and have it just hang there
    temp_inds = np.where(angular_size > end_size)
    if len(temp_inds[0]) > 0:
        max_size_ind = temp_inds[0][0]
        angular_size[max_size_ind:] = end_size
    # divide by  2 to get spot radius
    angular_size = angular_size / 2

    return time_steps, angular_size
