import time
import numpy as np

from flyvr.cnc import CncThread

def main(absVel=0.04, acc=0.03, tDur=4, minVel=0.025, tPause=60e-3, tSleep=10e-3, tExpDur=10):
    cncThread = CncThread()
    cncThread.start()

    tExp = time.time()
    state = False
    dir = True
    while time.time() - tExp < tExpDur:
        dir = not dir
        vel = absVel if dir else -absVel
        tStart = time.time()
        while time.time() - tStart < tDur:
            if state:
                cncThread.setVel(0, vel)
            else:
                cncThread.setVel(0, 0)
            time.sleep(tPause)
            state = not state

    cncThread.setVel(0, 0)
    time.sleep(0.1)
    cncThread.stop()

    print('average period:', cncThread.avePeriod)
    print('number of iterations:', cncThread.iterCount)
                    
if __name__=='__main__':
    main()
