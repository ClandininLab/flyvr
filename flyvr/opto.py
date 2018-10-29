import serial, platform
import os.path

from math import pi
from time import sleep, time
from threading import Lock, Thread
import serial.tools.list_ports

from flyvr.service import Service
from flyvr.util import serial_number_to_comport

class OptoService:
    ON_COMMAND = 0xbe
    OFF_COMMAND = 0xef

    def __init__(self, com=None):
        # set defaults
        if com is None:
            if platform.system() == 'Linux':
                com = serial_number_to_comport('7563830303735130C030')
            else:
                raise Exception('Opto not supported on this platform.')

        self.pulse_lock = Lock()
        self.log_lock = Lock()
        self.log_file = None

        # set up serial connection
        self.ser = serial.Serial(port=com, baudrate=9600)
        sleep(2)

    def on(self):
        self.log('on')
        self.write(self.ON_COMMAND)

    def off(self):
        self.log('off')
        self.write(self.OFF_COMMAND)

    def write(self, cmd):
        self.ser.write(bytearray([cmd]))

    def pulse(self, duration=1):
        def target():
            with self.pulse_lock:
                self.on()
                sleep(duration)
                self.off()

        Thread(target=target).start()

    def log(self, led_status):
        with self.log_lock:
            if self.log_file is not None:
                self.log_file.write('{}, {}\n'.format(time(), led_status))
                self.log_file.flush()

    def start_logging(self, exp_dir):
        with self.log_lock:
            if self.log_file is not None:
                self.log_file.close()
            self.log_file = open(os.path.join(exp_dir, 'opto_log.txt'), 'w')
            self.log_file.write('time, LED Status\n')

    def stop_logging(self):
        with self.log_lock:
            if self.log_file is not None:
                self.log_file.close()
            self.log_file = None