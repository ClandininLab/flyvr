import serial, platform, os.path

from threading import Thread, Lock, Event
from time import time, sleep

from flyvr.util import serial_number_to_comport
from flyvr.service import Service

class TempMonitor(Service):
    def __init__(self, maxTime=12e-3):
        serial_port = None

        if platform.system() == 'Darwin':
            serial_port = '/dev/tty.usbmodem1411'
        elif platform.system() == 'Linux':
            try:
                serial_port = serial_number_to_comport('85735313932351507170')
            except:
                print('### Could not connect to temperature Arduino ###')
        else:
            serial_port = 'COM4'

        serial_baud = 9600
        serial_timeout = 4
        shutdown_flag = Event()

        # save settings
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout
        self.shutdown_flag = shutdown_flag

        # serial connection
        self.conn = None

        # try to connect to the serial port
        try:
            self.conn = serial.Serial(self.serial_port, self.serial_baud, timeout=self.serial_timeout)
            print('Successfully connected to temperature arduino (port {}).'.format(self.serial_port))
        except:
            print('Failed to connect with temperature arduino (port {}).'.format(self.serial_port))
            return

        # make sure the serial buffer is initialized properly
        sleep(1.0)
        self.conn.reset_input_buffer()

        self.temp = None
        self.humd = None

        # File handle for logging
        self.logLock = Lock()
        self.logFile = None
        self.logFull = None
        self.logState = False

        # call constructor from parent
        super().__init__(maxTime=maxTime)

    def loopBody(self):
        # read temp
        self.read_temp()

        # write logs
        with self.logLock:
            if self.logState:
                #logStr = 'tada'
                logStr = (str(time()) + ',' +
                          str(self.temp) + ',' +
                          str(self.humd) + '\n')
                self.logFile.write(logStr)

        sleep(1)

    def read_temp(self):
        raw_data = str(self.conn.readline())
        parts = raw_data.split(',')
        self.temp = parts[1].strip()
        self.humd = parts[2].strip()

    def startLogging(self, logFile):
        with self.logLock:
            # save log state
            self.logState = True

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

            # open new log file
            self.logFile = open(logFile, 'w')
            self.logFile.write('t,temp,humd\n')

    def stopLogging(self):
        with self.logLock:
            # save log state
            self.logState = False

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()