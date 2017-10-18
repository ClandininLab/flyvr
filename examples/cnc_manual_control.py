import time
import pygame
from cnc import CNC

def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    clock = pygame.time.Clock()
    
    cnc = CNC()

    maxVel = 0.075
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
            inputX = -maxVel
        elif pressed[pygame.K_UP]:
            inputX = +maxVel

        inputY = 0
        if pressed[pygame.K_RIGHT]:
            inputY = maxVel
        elif pressed[pygame.K_LEFT]:
            inputY = -maxVel

        if pressed[pygame.K_s]:
            print(cnc.status.posX, cnc.status.posY)

        velX = alpha*velX + (1-alpha)*inputX
        velY = alpha*velY + (1-alpha)*inputY

        cnc.setVel(velX, velY)

        pygame.event.get()                
        
        screen.fill((0, 0, 0))
        pygame.display.flip()
        
        clock.tick(60)
                
if __name__=='__main__':
    main()
