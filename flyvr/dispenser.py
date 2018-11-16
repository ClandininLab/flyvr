#!/usr/bin/env python

import serial, platform, os.path
import numpy as np
import matplotlib.pyplot as plt

from threading import Thread, Lock, Event
from time import time, sleep

from flyrpc.transceiver import MySocketServer
from flyrpc.util import get_kwargs

from flyvr.util import serial_number_to_comport

def format_values(values, delimeter='\t', line_ending='\n'):
    retval = [str(value) for value in values]
    retval = delimeter.join(retval)
    retval += line_ending

    return retval

class FlyDispenser:
    def __init__(self, serial_port=None, serial_baud=None, serial_timeout=None, shutdown_flag=None):
        # set defaults
        if serial_port is None:
            if platform.system() == 'Darwin':
                serial_port = '/dev/tty.usbmodem1411'
            elif platform.system() == 'Linux':
                try:
                    serial_port = serial_number_to_comport('557393232373516180D1')
                except:
                    print('Could not connect to fly dispenser Arduino.')
            else:
                serial_port = 'COM4'

        if serial_baud is None:
            serial_baud = 115200

        if serial_timeout is None:
            serial_timeout = 4

        if shutdown_flag is None:
            shutdown_flag = Event()

        # save settings
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout
        self.shutdown_flag = shutdown_flag

        # save parameters
        self.num_pixels = 128
        self.gate_start = 25
        self.gate_end = 45
        self.max_usable_pixel = 90

        # serial connection
        self.conn = None
        self.synced = False

        # dispenser state
        self.state = 'Reset'
        self.timer_ref = None

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

        # initialize display settings
        self.display_type = 'raw'
        self.display_threshold = -11
        self.gate_clear_threshold = -8
        self.fly_passed_threshold = -11
        self.num_needed_pixels = 2

        # manual command locking
        self.should_release = Event()
        self.should_open = Event()
        self.should_close = Event()
        self.should_calibrate_gate = Event()
        self.gate_state = None

        # frame locking
        self.display_frame_lock = Lock()
        self._display_frame = None

        # log file management
        self.log_lock = Lock()
        self.log_time_ref = None
        self.raw_data_file = None
        self.open_times_file = None
        self.close_times_file = None

    @property
    def display_frame(self):
        with self.display_frame_lock:
            return self._display_frame

    @display_frame.setter
    def display_frame(self, value):
        with self.display_frame_lock:
            self._display_frame = value

    def loop(self):
        if self.serial_port is None:
            return

        # save the start time
        self.log_time_ref = time()

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

        # main loop
        while not self.shutdown_flag.is_set():
            self.loop_body()

        # cleanup tasks
        self.send_close_gate_command()
        self.conn.close()

    def loop_body(self):
        # read next frame
        self.read_frame()

        # handle manual command outside of state machine
        # this will always send the state machine back to Idle
        if self.should_open.is_set():
            self.send_open_gate_command()
            self.state ='Idle'
            print('Dispenser: going to Idle state.')

        if self.should_close.is_set():
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
            self.state = 'Idle'
            print('Dispenser: going to Idle state.')
        elif self.state == 'Idle':
            if self.should_release.is_set():
                self.send_open_gate_command()
                self.start_timer()
                self.state = 'PreReleaseDelay'
                print('Dispenser: going to PreReleaseDelay state.')
        elif self.state == 'PreReleaseDelay':
            if self.timer_done(0.5):
                self.state = 'LookForFly'
                print('Dispenser: going to LookForFly state.')
        elif self.state == 'LookForFly':
            if self.gate_clear and self.fly_passed:
                self.send_close_gate_command()
                self.state = 'Idle'
                print('Dispenser: going to Idle state.')
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
            self.log(self.raw_data_file, frame)

            # save previous frame for difference calculation if desired
            self.prev_frame = self.raw_data

            # add frame to history
            self.raw_data = np.array(frame)
        else:
            if self.synced:
                print('Dispenser camera lost sync')
                synced = False

    @property
    def gate_clear(self):
        if self.background_region is None:
            return False

        diff = (self.raw_data[self.gate_start:self.gate_end] -
                self.background_region[self.gate_start:self.gate_end])

        return np.all(diff > self.gate_clear_threshold)

    @property
    def fly_passed(self):
        if self.background_region is None:
            return False

        #diff = (self.raw_data[self.gate_end:self.max_usable_pixel] -
        #        self.background_region[self.gate_end:self.max_usable_pixel])

        diff = -np.abs(self.raw_data[self.gate_end:self.max_usable_pixel] -
                       self.prev_frame[self.gate_end:self.max_usable_pixel])

        return np.sum(diff < self.fly_passed_threshold) > self.num_needed_pixels

    def start_timer(self):
        self.timer_ref = time()

    def timer_done(self, duration):
        return (time() - self.timer_ref) > duration

    def log_time(self):
        return time() - self.log_time_ref

    def send_open_gate_command(self):
        print('Dispenser: opening gate...')
        self.conn.write(bytes([1]))
        self.log(self.open_times_file, [self.log_time()])
        self.gate_state = 'open'

    def send_close_gate_command(self):
        print('Dispenser: closing gate...')
        self.conn.write(bytes([0]))
        self.log(self.close_times_file, [self.log_time()])
        self.gate_state = 'closed'

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
        for f in [self.raw_data_file, self.open_times_file, self.close_times_file]:
            if f is not None:
                f.close()

    def log(self, f, values):
        with self.log_lock:
            if f is not None:
                f.write(format_values(values))
                f.flush()

    def start_logging(self, exp_dir):
        with self.log_lock:
            self.close_all_open_files()

            self.raw_data_file = open(os.path.join(exp_dir, 'raw_gate_data.txt'), 'w')
            self.open_times_file = open(os.path.join(exp_dir, 'open_gate_data.txt'), 'w')
            self.close_times_file = open(os.path.join(exp_dir, 'close_gate_data.txt'), 'w')

    def stop_logging(self):
        with self.log_lock:
            self.close_all_open_files()

            self.raw_data_file = None
            self.open_times_file = None
            self.close_times_file = None

def main():
    # start the server
    kwargs = get_kwargs()
    if kwargs['port'] is None:
        kwargs['port'] = 39855
    server = MySocketServer(host=kwargs['host'], port=kwargs['port'], name='DispenseServer', threaded=True)

    # create fly dispenser object
    dispenser = FlyDispenser(serial_port=kwargs['serial_port'], serial_baud=kwargs['serial_baud'],
                             serial_timeout=kwargs['serial_timeout'], shutdown_flag = server.shutdown_flag)

    # start the dispener loop
    t = Thread(target=dispenser.loop)
    t.start()

    # register methods
    server.register_function(dispenser.start_logging)
    server.register_function(dispenser.stop_logging)
    server.register_function(dispenser.release_fly)
    server.register_function(dispenser.open_gate)
    server.register_function(dispenser.close_gate)
    server.register_function(dispenser.calibrate_gate)
    server.register_function(dispenser.set_display_threshold)
    server.register_function(dispenser.set_fly_passed_threshold)
    server.register_function(dispenser.set_gate_clear_threshold)
    server.register_function(dispenser.set_num_needed_pixels)
    server.register_function(dispenser.set_display_type)

    # run the main event loop using matplotlib

    should_plot = kwargs.get('should_plot', True)
    plot_interval = kwargs.get('plot_interval', 0.01)

    if should_plot:
        plot_data = np.zeros((dispenser.num_pixels, dispenser.num_pixels))
        lines = plt.matshow(plot_data, vmin=0, vmax=255)

    # run the main event loop using matplotlib
    while not server.shutdown_flag.is_set():
        if should_plot:
            display_frame = dispenser.display_frame
            if display_frame is not None:
                plot_data = np.vstack(([display_frame], plot_data[0:-1, :]))
                lines.set_data(plot_data)

        server.process_queue()

        # pause function is required to actually update the display and provide GUI functionality
        plt.pause(plot_interval)

    # wait for dispenser thread to finish
    t.join()


if __name__ == '__main__':
    main()