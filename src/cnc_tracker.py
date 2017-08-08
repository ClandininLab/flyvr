import numpy as np
import cv2
import time
from math import pi
import serial

def nothing(x):
    pass

class CncStatus:
    def __init__(self, status):
        self.limN = bool((status[0] >> 1) & 1 == 0)
        self.limS = bool((status[0] >> 2) & 1 == 0)
        self.limE = bool((status[0] >> 3) & 1 == 0)
        self.limW = bool((status[0] >> 4) & 1 == 0)
        self.posX = self.posFromByteArr(status[1:4])
        self.posY = self.posFromByteArr(status[4:7])

    @property
    def anyLim(self):
        return self.limN or self.limS or self.limE or self.limW

    def posFromByteArr(self, byteArr):
        intPos = int.from_bytes(byteArr, byteorder='big', signed=True)
        return float(intPos)*25e-6

class CNC:
    def __init__(self, com='COM4', baud=9600):
        self.ser = serial.Serial(com, baud, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
        
        self.lastVelX = 0
        self.lastVelY = 0

    def getStatus(self):
        return self.setVel(velX=None, velY=None)

    def setVel(self, velX, velY):
        if velX is None:
            velX = self.lastVelX
        if velY is None:
            velY = self.lastVelY
            
        byteArrOut = bytearray(self.velByte(velX) + self.velByte(velY))
        self.ser.write(byteArrOut)

        self.lastVelX = velX
        self.lastVelY = velY

        byteArrIn = bytearray(self.ser.read(7))
        return CncStatus(byteArrIn)

    def velByte(self, v):
        frac = abs(v)/0.75 # 0.75m/s is the max speed
        intVal = round(frac*32767)
        if v > 0:
            intVal = intVal | 0x8000
        highByte = (intVal >> 8) & 0xFF
        lowByte = intVal & 0xFF
        return [highByte, lowByte]

def main():
    timestr = time.strftime("%Y%m%d-%H%M%S")
    f = open(timestr + '.csv', 'w')

    cnc = CNC()
    time.sleep(2)

    cv2.namedWindow('frame')
    cv2.createTrackbar('thresh','frame',120,255,nothing)

    cap = cv2.VideoCapture(0)
    px_per_m = 14334

    fc = 0.4 # hertz
    a = 2*pi*fc
    b = a**2

    integX = 0
    integY = 0
    maxVel = 0.075

    lastTime = time.time()

    velX = 0
    velY = 0
    decayFactor = 0.9

    while(True):
        # Capture frame-by-frame
        ret, im = cap.read()

        # Our operations on the frame come here
        im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        thresh = cv2.getTrackbarPos('thresh', 'frame')
        ret, im  = cv2.threshold(im, thresh, 255, cv2.THRESH_BINARY_INV)
        im2, contours, h = cv2.findContours(im, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # read current time
        thisTime = time.time()

        flyPresent = False
        camX = 0.0
        camY = 0.0
            
        if len(contours) > 0:
            maxC = max(contours, key = cv2.contourArea)
            cv2.drawContours(im, [maxC], -1, (128,255,0), 3)
            M = cv2.moments(maxC)
            
            if float(M["m00"]) > 0:
                flyPresent = True
                    
                rows, cols = im.shape
                camX = ((float(M["m10"]) / float(M["m00"])) - float(cols)/2.0)/px_per_m 
                camY = ((float(M["m01"]) / float(M["m00"])) - float(rows)/2.0)/px_per_m

        # compute velX and velY
        if flyPresent:
            # compute integrals
            dt = thisTime - lastTime
            integX = integX + camX*dt
            integY = integY + camY*dt

            # compute velocities
            velX = a*camX + b*integX
            velY = a*camY + b*integY
            velX = float(np.sign(velX))*min(abs(velX), maxVel)
            velY = float(np.sign(velY))*min(abs(velY), maxVel)
        else:
            # otherwise decay current velocity
            velX = decayFactor*velX
            velY = decayFactor*velY

        # update CNC velocity and log position
        status = cnc.setVel(velX, velY)

        # write log file
        f.write(str(thisTime) + ', ')
        f.write(str(flyPresent) + ', ')
        f.write(str(camX) + ', ' + str(camY) + ', ')
        f.write(str(status.posX) + ', ' + str(status.posY) + '\n')

        # update lastTime variable
        lastTime = thisTime
        
        # Display the resulting frame
        cv2.imshow('frame', im)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cnc.setVel(0, 0)

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

if __name__=='__main__':
    main()
