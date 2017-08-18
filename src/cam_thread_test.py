import time

from camera import CamThread
from cnc import CncThread

def main():
    camThread = CamThread()
    cncThread = CncThread()
    
    camThread.start()
    cncThread.start()
    
    time.sleep(10)

    camThread.stop()
    cncThread.stop()

    print(camThread.avePeriod)
    print(camThread.iterCount)

    print(cncThread.avePeriod)
    print(cncThread.iterCount)
                    
if __name__=='__main__':
    main()
