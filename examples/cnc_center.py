import time

from math import pi

from cnc import CncThread

def clamp(v, minV=-0.03, maxV=0.03):
    if v < minV:
        return minV
    elif v > maxV:
        return maxV
    else:
        return v

def main():
    centerX = 0.401
    centerY = 0.405

    #centerX = 0.01
    #centerY = 0.01

    k = 2*pi
    tol = 1e-3
    
    cnc = CncThread()
    cnc.start()

    # wait for initial position report    
    time.sleep(0.1)

    # move to edge
    cnc.setVel(-0.02, -0.02)
    while(not cnc.status.limS or not cnc.status.limW):
        cnc.setVel(-0.02, -0.02)

    errX = centerX - cnc.status.posX
    errY = centerY - cnc.status.posY

    while abs(errX) > tol or abs(errY) > tol:
        errX = centerX - cnc.status.posX
        errY = centerY - cnc.status.posY

        velX = clamp(k*errX)
        velY = clamp(k*errY)

        cnc.setVel(velX, velY)

        time.sleep(10e-3)

    # set velocity to zero and wait for it to take effect
    cnc.setVel(0, 0)
    time.sleep(0.1)
    
    cnc.stop()
                       
if __name__=='__main__':
    main()
