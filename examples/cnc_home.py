import time

from flyvr.cnc import CncThread

def main():
    velX = -0.02
    velY = -0.02
    
    cnc = CncThread()
    cnc.start()

    # wait for initial position report    
    time.sleep(0.1)

    # move to edge
    cnc.setVel(velX, velY)
    while(not cnc.status.limS or not cnc.status.limW):
        cnc.setVel(velX, velY)

    # set velocity to zero and wait for it to take effect
    cnc.setVel(0, 0)
    time.sleep(0.1)
    
    cnc.stop()
                
if __name__=='__main__':
    main()
