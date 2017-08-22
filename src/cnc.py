import serial
import os.path

import time

from service import Service
from threading import Lock

class CncThread(Service):
    def __init__(self):
        # Serial I/O interface to CNC
        self.cnc = CNC()

        # Lock for communicating velocity changes to CNC
        self.cmdLock = Lock()
        self.setVel(0, 0)

        # Lock for communicating status changes from CNC
        self.statusLock = Lock()
        self.status = None

        # call constructor from parent        
        super().__init__()

    # overriding method from parent...
    def loopBody(self):
        # read command
        cmdX, cmdY = self.getVel()

        # write velocity
        self.cnc.setVel(cmdX, cmdY)

        # store status
        self.status = self.cnc.status

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

class CncStatus:
    def __init__(self, status):
        # compute checksum
        cksum = sum(status[0:5]) & 0xFF

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
        return (0b11100001 | self.status[0]) != 0xFF

    @property
    def posX(self):
        return CncStatus.posFromByteArr(self.status[1:3])

    @property
    def posY(self):
        return CncStatus.posFromByteArr(self.status[3:5])

    @staticmethod
    def posFromByteArr(byteArr):
        intPos = int.from_bytes(byteArr, byteorder='big', signed=True)
        return float(intPos)*25e-6

class CNC:
    def __init__(self, com='COM5', baud=400000):
        self.ser = serial.Serial(port=com, baudrate=baud, bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        time.sleep(2)

    def setVel(self, velX, velY):
        # format velocity command
        byteArrOut = CNC.velByte(velX) + CNC.velByte(velY)

        # compute checksum
        cksum = sum(byteArrOut) & 0xFF

        # append checksum
        byteArrOut += bytearray([cksum])

        # send command over serial interface
        self.ser.write(byteArrOut)

        # read position
        byteArrIn = bytearray(self.ser.read(6))
        self.status = CncStatus(byteArrIn)

    def __del__(self):
        self.setVel(0, 0)
        self.ser.close()
    
    @staticmethod
    def velByte(v):
        intVal = round(abs(v)*43689) # 0.75 m/s is the max speed, 32767 is the maximum argument

        # check that the speed is not too high
        if intVal > 32767:
            raise Exception('Requested speed is too high.')
        
        # indicate direction
        if v > 0:
            intVal |= 0x8000

        return intVal.to_bytes(2, byteorder='big')
