import time
import numpy as np

from flyvr.cnc import CncThread

def main(velY=1e-3, acc=0.03,tDur=15, minVel=0.025, tPause=30e-3, tSleep=10e-3):
    cncThread = CncThread()
    cncThread.start()

    cncThread.setVel(0, velY)

    # curr = float(np.sign(velY))*minVel
    # lastTime = time.time()
    # while True:
    #     thisTime = time.time()
    #     dt = thisTime - lastTime
    #     dV = float(np.sign(velY))*acc*dt
    #     if abs(curr+dV) > abs(velY):
    #         cncThread.setVel(0, velY)
    #         break
    #     else:
    #         curr += dV
    #         if abs(curr) > minVel:
    #             cncThread.setVel(0, curr)
    #         else:
    #             cncThread.setVel(0, 0)
    #     lastTime = thisTime
    #     time.sleep(tSleep)

    time.sleep(tDur)

    # tStart = time.time()
    # state = False
    # while time.time() - tStart < tDur:
    #     state=True
    #     if state:
    #         cncThread.setVel(velX, velY)
    #     else:
    #         cncThread.setVel(0, 0)
    #     time.sleep(tPause)
    #     state = not state

    # curr = velY
    # lastTime = time.time()
    # while True:
    #     thisTime = time.time()
    #     dt = thisTime - lastTime
    #     dV = -float(np.sign(velY))*acc*dt
    #     if (velY < 0 and (curr+dV) > -minVel) or (velY > 0 and (curr+dV) < minVel):
    #         cncThread.setVel(0, velY)
    #         break
    #     else:
    #         curr += dV
    #         if abs(curr) > minVel:
    #             cncThread.setVel(0, curr)
    #         else:
    #             cncThread.setVel(0, 0)
    #     lastTime = thisTime
    #    time.sleep(tSleep)

    cncThread.setVel(0, 0)
    time.sleep(0.1)
    cncThread.stop()

    print('average period:', cncThread.avePeriod)
    print('number of iterations:', cncThread.iterCount)
                    
if __name__=='__main__':
    main()
