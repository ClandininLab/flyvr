import serial
import os.path

from time import sleep, perf_counter

from service import Service
from threading import Lock

class CncThread(Service):
    def __init__(self, maxTime=10e-3, logging=True):
        # Serial I/O interface to CNC
        self.cnc = CNC()

        # Lock for communicating velocity changes to CNC
        self.cmdLock = Lock()
        self.setVel(0, 0)

        # Lock for communicating status changes from CNC
        self.statusLock = Lock()
        self.status = None

        # File handle for logging
        self.logging = logging
        if self.logging:
            self.fPtr = open('cnc.txt', 'w')
            self.fPtr.write('t,x,y\n')

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
        if self.logging:
            logStr = (str(perf_counter()) + ',' +
                      str(status.posX) + ',' +
                      str(status.posY) + '\n')
            self.fPtr.write(logStr)

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
                 com='COM5', 
                 baud=115200,
                 maxSpeed=0.75, # m/s
                 bytesPerVel=3
                 ):
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
