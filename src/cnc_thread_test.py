import time
from cnc import CncThread

def main():
    cncThread = CncThread()
    cncThread.start()
    for k in range(1000):
        cncThread.setVel(0, 0)
        time.sleep(1e-3)
    cncThread.stop()

    print(cncThread.avePeriod)
    print(cncThread.iterCount)
                    
if __name__=='__main__':
    main()
