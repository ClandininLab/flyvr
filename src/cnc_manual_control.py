import serial
import time
import pygame

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
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    clock = pygame.time.Clock()
    
    cnc = CNC()
    time.sleep(2)

    velX = 0
    velY = 0
    alpha = 0.8
    
    while True:
        pressed = pygame.key.get_pressed()

        if pressed[pygame.K_ESCAPE]:
            cnc.setVel(0, 0)
            return

        inputX = 0
        if pressed[pygame.K_DOWN]:
            inputX = -0.075
        elif pressed[pygame.K_UP]:
            inputX = +0.075

        inputY = 0
        if pressed[pygame.K_RIGHT]:
            inputY = 0.075
        elif pressed[pygame.K_LEFT]:
            inputY = -0.075

        velX = alpha*velX + (1-alpha)*inputX
        velY = alpha*velY + (1-alpha)*inputY

        cnc.setVel(velX, velY)

        pygame.event.get()                
        
        screen.fill((0, 0, 0))
        pygame.display.flip()
        
        clock.tick(60)
                
if __name__=='__main__':
    main()
