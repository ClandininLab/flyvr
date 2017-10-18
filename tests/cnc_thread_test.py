import time

from flyvr.cnc import CncThread

def main():
    cncThread = CncThread()
    cncThread.start()
    for k in range(1000):
        cncThread.setVel(0, 0)
        time.sleep(1e-3)
    cncThread.stop()

    print('average period:', cncThread.avePeriod)
    print('number of iterations:', cncThread.iterCount)
                    
if __name__=='__main__':
    main()
