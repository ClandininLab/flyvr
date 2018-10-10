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
        self.gate_start = 30
        self.gate_end = 43

        # serial connection
        self.conn = None

        # dispenser state
        self.state = 'Reset'
        self.timer_ref = None

        # try to load gate region data
        try:
            self.gate_region = np.load('gate_region.npy')
            print('Successfully loaded gate_region data')
        except:
            print('Could not load gate_region data.  Please re-calibrate.')
            self.gate_region = None

        # history of last few frames
        self.hist = np.zeros((2, self.num_pixels))

        # manual command locking
        self.should_release = Event()
        self.should_open = Event()
        self.should_close = Event()
        self.should_calibrate_gate = Event()

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
        if self.should_open.is_set():
            self.should_open.clear()
            self.send_open_gate_command()

        if self.should_close.is_set():
            self.should_close.clear()
            self.send_close_gate_command()

        if self.should_calibrate_gate.is_set():
            print('Manually calibrating gate...')
            self.should_calibrate_gate.clear()
            self.gate_region = self.hist[0, self.gate_start:self.gate_end]
            np.save('gate_region', self.gate_region)

        # update state machine
        if self.state == 'Reset':
            self.send_close_gate_command()
            self.state = 'Idle'
            print('Dispenser: going to Idle state.')
        elif self.state == 'Idle':
            if self.should_release.is_set():
                self.should_release.clear()
                self.send_open_gate_command()
                self.start_timer()
                self.state = 'PreReleaseDelay'
                print('Dispenser: going to PreReleaseDelay state.')
        elif self.state == 'PreReleaseDelay':
            if self.timer_done(0.1):
                self.state = 'LookForFly'
                print('Dispenser: going to LookForFly state.')
        elif self.state == 'LookForFly':
            if self.gate_clear and self.fly_passed:
                self.send_close_gate_command()
                self.state = 'Idle'
                print('Dispenser: going to Idle state.')
        else:
            raise Exception('Invalid state.')

    def read_frame(self):
        while True:
            start_byte = self.conn.read(1)[0]

            if int(start_byte) == 0:
                # read raw data into a list
                frame = self.conn.read(self.num_pixels)
                frame = list(frame)

                # write frame to variable for matplotlib display
                self.display_frame = frame

                # write frame to file
                self.log(self.raw_data_file, frame)

                # add frame to history
                self.hist = np.vstack(([frame], self.hist[0:-1, :]))

                return

    @property
    def gate_clear(self, gate_thresh=100):
        if self.gate_region is None:
            return False

        gate_difference = self.gate_region-self.hist[0, self.gate_start:self.gate_end]
        gate_sum = np.sum(gate_difference)
        return (gate_sum < gate_thresh)

    @property
    def fly_passed(self, fly_threshold=5, num_needed_pixels=2):
        diff = self.hist[0, self.gate_end:] - self.hist[1, self.gate_end:]
        return np.sum(np.abs(diff) > fly_threshold) > num_needed_pixels

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

    def send_close_gate_command(self):
        print('Dispenser: closing gate...')
        self.conn.write(bytes([0]))
        self.log(self.close_times_file, [self.log_time()])

    def open_gate(self):
        self.should_open.set()

    def close_gate(self):
        self.should_close.set()

    def calibrate_gate(self):
        self.should_calibrate_gate.set()

    def release_fly(self):
        self.should_release.set()

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