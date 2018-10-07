#!/usr/bin/env python

import serial, platform, os.path
import numpy as np
import matplotlib.pyplot as plt

from threading import Thread, Lock, Event
from time import time, sleep

from flyrpc.transceiver import MySocketServer
from flyrpc.util import get_kwargs

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

        # serial connection
        self.conn = None

        # dispenser state
        self.state = 'Reset'
        self.timer_ref = None

        # history of last few frames
        self.hist = np.zeros((3, self.num_pixels))

        # manual command locking
        self.should_release_lock = Lock()
        self._should_release = False

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
    def should_release(self):
        with self.should_release_lock:
            return self._should_release

    @should_release.setter
    def should_release(self, value):
        with self.should_release_lock:
            self._should_release = value

    @property
    def display_frame(self):
        with self.display_frame_lock:
            return self._display_frame

    @display_frame.setter
    def display_frame(self, value):
        with self.display_frame_lock:
            self._display_frame = value

    def loop(self):
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
        self.close_gate()
        self.conn.close()

    def loop_body(self):
        self.read_frame()

        if self.state == 'Reset':
            self.close_gate()
            self.start_timer()
            self.state = 'ClosedGateStabilize'
        elif self.state == 'ClosedGateStabilize':
            if self.timer_done(3):
                self.background_close = np.mean(self.hist, axis=0)
                self.open_gate()
                self.start_timer()
                self.state = 'OpenGateStabilize'
        elif self.state == 'OpenGateStabilize':
            if self.timer_done(3):
                self.background_open = np.mean(self.hist, axis=0)
                self.close_gate()
                self.detect_gate()
                self.state = 'Idle'
        elif self.state == 'Idle':
            if self.should_release:
                self.open_gate()
                self.start_timer()
                self.state = 'PreReleaseDelay'
        elif self.state == 'PreReleaseDelay':
            if self.timer_done(1):
                self.state = 'LookForFly'
        elif self.state == 'LookForFly':
            if self.gate_clear and self.fly_passed:
                self.close_gate()
                self.start_timer()
                self.state = 'PostReleaseDelay'
        elif self.state == 'PostReleaseDelay':
            if self.timer_done(1):
                self.should_release = False
                self.state = 'Idle'
        else:
            raise Exception('Invalid state.')

    def detect_gate(self, half_gate_width=7):
        # find gate
        self.gate_difference = self.background_open - self.background_close
        self.gate_center = np.argmax(self.gate_difference)
        self.gate_start = self.gate_center-half_gate_width
        self.gate_end = self.gate_center+half_gate_width

        #BAD --- REMOVE!!!
        self.gate_start = 30
        self.gate_end = 43

        #for fly detection later
        self.gate_region = self.background_open[self.gate_start:self.gate_end]

        print('gate start: ', self.gate_start)
        print('gate end: ', self.gate_end)

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

    def open_gate(self):
        self.conn.write(bytes([1]))
        self.log(self.open_times_file, [self.log_time()])

    def close_gate(self):
        self.conn.write(bytes([0]))
        self.log(self.close_times_file, [self.log_time()])

    def release_fly(self):
        self.manual_command = 'ReleaseFly'

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

            self.raw_data_file = os.path.join(exp_dir, 'raw_gate_data.txt')
            self.open_times_file = os.path.join(exp_dir, 'open_gate_data.txt')
            self.close_times_file = os.path.join(exp_dir, 'close_gate_data.txt')

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