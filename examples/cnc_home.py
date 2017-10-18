import time
from cnc import CNC

def main():
    velX = -0.02
    velY = -0.02
    
    cnc = CNC()

    cnc.setVel(velX, velY)
    while(not cnc.status.limS or not cnc.status.limW):
        cnc.setVel(velX, velY)
                
if __name__=='__main__':
    main()
