#!/usr/bin/env python

import serial, platform, os.path
import numpy as np
import matplotlib.pyplot as plt

from threading import Thread, Lock, Event
from time import time, sleep

from flyrpc.transceiver import MySocketServer
from flyrpc.util import get_kwargs

from flyvr.util import serial_number_to_comport
from flyvr.service import Service

def format_values(values, delimeter='\t', line_ending='\n'):
    retval = [str(value) for value in values]
    retval = delimeter.join(retval)
    retval += line_ending

    return retval

class FlyDispenser(Service):
    def __init__(self, maxTime=12e-3):
        # set defaults

        serial_port = None

        if platform.system() == 'Darwin':
            serial_port = '/dev/tty.usbmodem1411'
        elif platform.system() == 'Linux':
            try:
                serial_number = '5573731323135121E0C2' #Arduino specific
                serial_port = serial_number_to_comport(serial_number)
            except:
                print('Could not connect to fly dispenser Arduino.')
                print("  **NOTE** if this is a new Arduino, you must:")
                print("\t (1) open: <path_to_flyvr_code>/flyvr/dispensor.py")
                print("\t (2) edit: serial_number to match the new Arduino.")
        else:
            serial_port = 'COM4'

        serial_baud = 115200
        serial_timeout = 4
        shutdown_flag = Event()

        # save settings
        self.serial_port = serial_port
        print('THIS IS SERIAL PORT:', self.serial_port)
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout
        self.shutdown_flag = shutdown_flag

        # save parameters
        self.num_pixels = 128
        self.gate_start = 25
        self.gate_end = 45
        self.diff = None

        # serial connection
        self.conn = None
        self.synced = False

        # dispenser state
        self.state = 'Reset'

        # set gate region file location
        this_file = os.path.abspath(os.path.expanduser(__file__))
        self.background_region_file = os.path.join(os.path.join(os.path.dirname(os.path.dirname(this_file)), 'calibration'), 'background_region.npy')

        # try to load gate region data
        try:
            self.background_region = np.load(self.background_region_file)
            print('Successfully loaded background_region data')
        except:
            print('Could not load background region data.  Please re-calibrate.')
            self.background_region = None

        # history of last few frames
        self.raw_data = np.zeros((self.num_pixels, ))

        # last frame
        self.prev_frame = None

        # # initialize display settings--- OLD SETTINGS
        # self.display_type = 'raw'
        # self.display_threshold = -11
        # self.gate_clear_threshold = -20
        # self.fly_passed_threshold = -11
        # self.num_needed_pixels = 2

        # initialize display settings--new settings with new camera 20201027
        self.display_type = 'raw'
        self.display_threshold = -11
        self.gate_clear_threshold = -20
        self.fly_passed_threshold = -3  ##this may need to be more negative if it is too sensitive
        self.num_needed_pixels = 2 # how many pixels in the gate exceeded the fly_passed_threshold, make smaller if not sensitive enough

        # manual command locking
        self.should_release = Event()
        self.should_open = Event()
        self.should_close = Event()
        self.should_calibrate_gate = Event()
        self.gate_state = None

        #for opening dispenser if it is closed too long in error
        self.prev_state = None
        self.closed_gate_timer = None
        self.no_fly_reopen_gate = False  #this should reset when the trial thread finds a fly
        self.closed_gate_wait_time = 180 #time in sec to wait to reopen gate after not finding fly

        # frame locking
        self.display_frame_lock = Lock()
        self._display_frame = None

        # log file management
        self.log_lock = Lock()
        self.raw_data_file = None
        self.gate_times_file = None

        # for logging the cause of gate opening and closing
        self.trigger = None

        # try to connect to the serial port
        try:
            self.conn = serial.Serial(self.serial_port, self.serial_baud, timeout=self.serial_timeout)
            print('Connected to {} at {} baud.'.format(self.serial_port, self.serial_baud))
        except:
            print('Failed to connect with {} at {} baud.'.format(self.serial_port, self.serial_baud))
            return

        # make sure the serial buffer is initialized properly
        sleep(1.0)
        self.conn.reset_input_buffer()

        # call constructor from parent
        super().__init__(maxTime=maxTime)

    @property
    def display_frame(self):
        with self.display_frame_lock:
            return self._display_frame

    @display_frame.setter
    def display_frame(self, value):
        with self.display_frame_lock:
            self._display_frame = value

    def loopBody(self):
        # read next frame
        self.read_frame()

        # handle manual command outside of state machine
        # this will always send the state machine back to Idle
        if self.should_open.is_set():
            self.trigger = 'manual'
            self.send_open_gate_command()
            self.state ='Idle'
            print('Dispenser: going to Idle state.')

        if self.should_close.is_set():
            self.trigger = 'manual'
            self.send_close_gate_command()
            self.state = 'Idle'
            print('Dispenser: going to Idle state.')

        # handle calibration
        if self.should_calibrate_gate.is_set():
            if self.gate_state == 'open':
                print('Calibrating gate...')
                self.background_region = self.raw_data
                print('background region:', self.background_region)
                np.save(self.background_region_file, self.background_region)
            else:
                print('Cannot calibrate gate.  Please issue an open_gate() command.')

            self.state = 'Idle'
            print('Dispenser: going to Idle state.')

        # update state machine
        if self.state == 'Reset':
            self.send_close_gate_command()
            self.prev_state = 'Reset'
            self.state = 'Idle'
            print('Dispenser: going to Idle state.')
        elif self.state == 'Idle':
            if self.should_release.is_set():
                self.trigger = 'auto'
                self.send_open_gate_command()
                self.start_timer()
                self.prev_state = 'Idle'
                self.state = 'PreReleaseDelay'
                print('Dispenser: going to PreReleaseDelay state.')
            # this is to fix when the dispenser closes without their being a fly in the tunnel
            #   or flies stuck in the tunnel
            if self.prev_state == 'LookForFly' and (time() - self.closed_gate_timer) >= self.closed_gate_wait_time:
                #self.no_fly_reopen_gate = True #this resets to false when trial detects a fly
                self.state = 'ReOpenGate'
                print("Dispenser: time's up!")
            # if self.prev_state == 'LookForFly' and self.no_fly_reopen_gate:   #if previous state was look for fly
            #     #have it go into restart
            #     self.trigger = 'auto'
            #     self.send_open_gate_command()
            #     self.start_timer()
            #     self.prev_state = 'Idle'
            #     self.state = 'PreReleaseDelay'
            #     print('Dispenser: going to PreReleaseDelay state after not finding fly.')
        elif self.state == 'PreReleaseDelay':
            if self.timer_done(0.5):
                self.prev_state = 'PreReleaseDelay'
                self.state = 'LookForFly'
                print('Dispenser: going to LookForFly state.')
        elif self.state == 'LookForFly':
            if self.gate_clear and self.fly_passed:
                self.trigger = 'auto'
                self.send_close_gate_command()
                self.prev_state = 'LookForFly'
                self.state = 'Idle'
                print('Dispenser: going to Idle state.')
        elif self.state == 'ReOpenGate':
            if self.prev_state == 'LookForFly':   #if previous state was look for fly--prevents it from continuously reopening after timer set
                #have it go into restart
                self.trigger = 'auto'
                self.send_open_gate_command()
                self.start_timer()
                self.prev_state = 'Idle'
                self.state = 'PreReleaseDelay'
                print('Dispenser: going to PreReleaseDelay state after not finding fly.')

        else:
            raise Exception('Invalid state.')

        # clear flags
        self.should_open.clear()
        self.should_close.clear()
        self.should_calibrate_gate.clear()
        self.should_release.clear()

    def read_frame(self):
        start_byte = self.conn.read(1)[0]
        if int(start_byte) == 0:
            if not self.synced:
                print('Dispenser camera is synced.')
                self.synced = True
            # read raw data into a list
            frame = self.conn.read(self.num_pixels)
            frame = list(frame)

            # write frame to variable for matplotlib display
            if self.display_type == 'raw':
                display_frame = frame
            elif self.display_type == 'corrected':
                display_frame = frame
                if self.background_region is not None:
                    display_frame -= self.background_region
            elif self.display_type == 'diff':
                display_frame = frame
                if self.prev_frame is not None:
                    display_frame = np.abs(self.prev_frame - frame)
            else:
                display_frame = frame
                if self.background_region is not None:
                    display_frame -= self.background_region
                display_frame = display_frame > self.display_threshold

            self.display_frame = display_frame

            # write frame to file
            self.log_raw(frame)

            # save previous frame for difference calculation if desired
            self.prev_frame = self.raw_data

            # add frame to history
            self.raw_data = np.array(frame)
        else:
            if self.synced:
                print('Dispenser camera lost sync')
                self.synced = False

    @property
    def gate_clear(self):
        if self.background_region is None:
            return False

        diff = (self.raw_data[self.gate_start:self.gate_end] -
                self.background_region[self.gate_start:self.gate_end])
        #print('gate_clear-diff', diff)
        return np.all(diff > self.gate_clear_threshold)

    @property
    def fly_passed(self):
        if self.background_region is None:
            return False

        #diff = (self.raw_data[self.gate_end:self.max_usable_pixel] -
        #        self.background_region[self.gate_end:self.max_usable_pixel])

        diff = -np.abs(self.raw_data[self.gate_end:] - self.prev_frame[self.gate_end:])
        #print('fly-passed-diff', diff)
        return np.sum(diff < self.fly_passed_threshold) > self.num_needed_pixels

    def start_timer(self):
        self.timer_ref = time()

    def timer_done(self, duration):
        return (time() - self.timer_ref) > duration

    def send_open_gate_command(self):
        print('Dispenser: opening gate...')
        self.conn.write(bytes([1]))
        self.gate_state = 'open'
        self.log_gate(time(), self.gate_state)

    def send_close_gate_command(self):
        print('Dispenser: closing gate...')
        self.conn.write(bytes([0]))
        self.gate_state = 'closed'
        self.log_gate(time(), self.gate_state)
        self.closed_gate_timer = time()  #to use for counting how long the gate has been closed

    def open_gate(self):
        self.should_open.set()

    def close_gate(self):
        self.should_close.set()

    def calibrate_gate(self):
        self.should_calibrate_gate.set()

    def release_fly(self):
        self.should_release.set()

    def set_display_type(self, type):
        self.display_type = type

    def set_display_threshold(self, value):
        self.display_threshold = value

    def set_gate_clear_threshold(self, value):
        self.gate_clear_threshold = value

    def set_fly_passed_threshold(self, value):
        self.fly_passed_threshold = value

    def set_num_needed_pixels(self, value):
        self.num_needed_pixels = value

    def close_all_open_files(self):
        for f in [self.raw_data_file, self.gate_times_file]:
            if f is not None:
                f.close()

    def log_gate(self, time, state):
        with self.log_lock:
            if self.gate_times_file is not None:
                self.gate_times_file.write('{}, {}, {}\n'.format(time, state, self.trigger))
                self.gate_times_file.flush()
                self.trigger = None

    def log_raw(self, frame):
        with self.log_lock:
            if self.raw_data_file is not None:
                self.raw_data_file.write(format_values(frame))
                self.raw_data_file.flush()

    def start_logging(self, exp_dir):
        with self.log_lock:
            self.close_all_open_files()

            self.raw_data_file = open(os.path.join(exp_dir, 'raw_gate_data.txt'), 'w')
            self.gate_times_file = open(os.path.join(exp_dir, 'gate_data.txt'), 'w')

    def stop_logging(self):
        with self.log_lock:
            self.close_all_open_files()

            self.raw_data_file = None
            self.gate_times_file = None
