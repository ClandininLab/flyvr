import serial, platform
import os.path

from math import pi
from time import sleep, time
from threading import Lock, Thread
import serial.tools.list_ports

from flyvr.service import Service
from flyvr.tracker import TrackThread
from flyvr.cnc import CncThread
from flyvr.camera import CamThread

from flyvr.util import serial_number_to_comport

class OptoThread(Service):
    ON_COMMAND = 0xbe
    OFF_COMMAND = 0xef

    def __init__(self, cncThread=None, camThread=None, TrackThread=None, use_opto=False):
        # Serial interface to opto arduino
        com = None
        if com is None:
            if platform.system() == 'Linux':
                com = serial_number_to_comport('557323235303519180B1')
            else:
                raise Exception('Opto not supported on this platform.')

        # set up serial connection
        self.ser = serial.Serial(port=com, baudrate=9600)
        sleep(2)
        
        # Setup locks
        self.pulseLock = Lock()
        self.logLock = Lock()
        self.logFile = None
        self.logState = False

        # Store thread handles
        self.camThread = camThread
        self.cncThread = cncThread
        self.TrackThread = TrackThread

        # Set the starting time
        self.trial_start_time = None

        # call constructor from parent        
        super().__init__()

    # overriding method from parent...
    def loopBody(self):
        # get latest camera position
        flyData = self.camThread.flyData          
        if flyData is not None:
            camX = flyData.flyX
            camY = flyData.flyY
            flyPresent = flyData.flyPresent
        else:
            camX = 0
            camY = 0
            flyPresent = False

        # get latest cnc position
        if self.cncThread.status is not None:
            cncX = self.cncThread.status.posX
            cncY = self.cncThread.status.posY
        else:
            cncX = 0
            cncY = 0

        # find fly position
        flyX = camX + cncX
        flyY = camY + cncY

        # temporary opto logic
        if flyX > self.TrackThread.center_pos_x:
            self.on()
        else:
            self.off()

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
        with self.logLock:
            if self.logFile is not None:
                self.logFile.write('{}, {}\n'.format(time(), led_status))
                self.logFile.flush()

    def startLogging(self, logFile):
        self.trial_start_time = time()
        with self.logLock:

            self.logState = True

            if self.logFile is not None:
                self.logFile.close()

            self.logFile = open(logFile, 'w')
            self.logFile.write('time, LED Status\n')

    def stopLogging(self):
        with self.logLock:

            self.logState = False

            if self.logFile is not None:
                self.logFile.close()