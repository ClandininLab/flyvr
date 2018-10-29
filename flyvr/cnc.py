import serial, platform

from math import pi
from time import sleep, time
from threading import Lock
import serial.tools.list_ports

from flyvr.service import Service
from flyvr.util import serial_number_to_comport

class CncThread(Service):
    def __init__(self, maxTime=12e-3):
        # Serial I/O interface to CNC
        self.cnc = CNC()

        # Lock for communicating velocity changes to CNC
        self.cmdLock = Lock()
        self.cmdX = 0
        self.cmdY = 0

        # Lock for communicating status changes from CNC
        self.statusLock = Lock()
        self._status = None

        # File handle for logging
        self.logLock = Lock()
        self.logFile = None
        self.logState = False

        # call constructor from parent        
        super().__init__(maxTime=maxTime)

    # overriding method from parent...
    def loopBody(self):
        # read command
        cmdX, cmdY = self.getVel()

        # write velocity, get status
        status = self.cnc.setVel(cmdX, cmdY)

        # store status
        self.status = status

        # log status
        logState, logFile = self.getLogState()
        if logState:
            logStr = (str(time()) + ',' +
                      str(status.posX) + ',' +
                      str(status.posY) + '\n')
            logFile.write(logStr)

    def setVel(self, cmdX, cmdY):
        with self.cmdLock:
            self.cmdX, self.cmdY = cmdX, cmdY

    def getVel(self):
        with self.cmdLock:
            return self.cmdX, self.cmdY

    @property
    def status(self):
        with self.statusLock:
            return self._status

    @status.setter
    def status(self, val):
        with self.statusLock:
            self._status = val

    def startLogging(self, logFile):
        with self.logLock:
            # save log state
            self.logState = True

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

            # open new log file if desired
            self.logFile = open(logFile, 'w')
            self.logFile.write('t,x,y\n')

    def stopLogging(self):
        with self.logLock:
            # save log state
            self.logState = False

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

    def getLogState(self):
        with self.logLock:
            return self.logState, self.logFile

class CncStatus:
    def __init__(self, status):
        # compute checksum
        cksum = sum(status[0:5]) & 0xff

        # test checksum
        if cksum != status[5]:
            raise Exception('Status checksum invalid')

        # look for communication error
        if status[0] & 1 == 1:
            raise Exception('Checksum error reported by Arduino.')

        # save status report
        self.status = status

    @property
    def limN(self):
        return bool((self.status[0] >> 1) & 1 == 0)

    @property
    def limS(self):
        return bool((self.status[0] >> 2) & 1 == 0)

    @property
    def limE(self):
        return bool((self.status[0] >> 3) & 1 == 0)

    @property
    def limW(self):
        return bool((self.status[0] >> 4) & 1 == 0)

    @property
    def anyLim(self):
        return (0b11100001 | self.status[0]) != 0xff

    @property
    def posX(self):
        return CncStatus.posFromByteArr(self.status[1:3])

    @property
    def posY(self):
        return CncStatus.posFromByteArr(self.status[3:5])

    @staticmethod
    def posFromByteArr(byteArr):
        intPos = int.from_bytes(byteArr, byteorder='big', signed=True)
        return intPos*25e-6

class CNC:
    def __init__(self,
                 com=None, 
                 baud=115200,
                 maxSpeed=0.75, # m/s
                 bytesPerVel=3
                 ):
        # set defaults
        if com is None:
            if platform.system() == 'Linux':
                com = serial_number_to_comport('75330303035351E081A1')
            else:
                com = 'COM5'

        # store settings
        self.maxSpeed = maxSpeed
        self.bytesPerVel = bytesPerVel

        # set up serial connection
        self.ser = serial.Serial(port=com, baudrate=baud, bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        sleep(2)

    def setVel(self, velX, velY):
        # format velocity command
        byteArrOut = self.velByte(velX) + self.velByte(velY)

        # compute checksum
        ckSumOut = sum(byteArrOut) & 0xff

        # append checksum
        byteArrOut += bytearray([ckSumOut])

        # send command over serial interface
        self.ser.write(byteArrOut)

        # read position
        byteArrIn = bytearray(self.ser.read(6))

        # return status
        return CncStatus(byteArrIn)

    def __del__(self):
        self.setVel(0, 0)
        self.ser.close()
    
    def velByte(self, v):
        # compute maximum integer argument to be sent to Arduino
        signBit = (1 << ((8*self.bytesPerVel)-1))
        maxIntArg = signBit - 1

        # convert speed to integer representation
        intVal = int(round(abs(v)*maxIntArg/self.maxSpeed))

        # check that the speed is not too high
        if intVal > maxIntArg:
            raise Exception('Requested speed is too high.')
        
        # indicate direction
        if v > 0:
            intVal |= signBit

        return intVal.to_bytes(self.bytesPerVel, byteorder='big', signed=False)

def cnc_home(velX=-0.02, velY=-0.02):
    cnc = CncThread()
    cnc.start()

    # wait for initial position report
    sleep(0.1)

    # move to edge
    cnc.setVel(velX, velY)
    while (not cnc.status.limS or not cnc.status.limW):
        cnc.setVel(velX, velY)

    # set velocity to zero and wait for it to take effect
    cnc.setVel(0, 0)
    sleep(0.1)

    cnc.stop()
