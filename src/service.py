from time import time
from threading import Thread, Lock

class Service:
    def __init__(self):
        self.doneLock = Lock()
        self.done = False

    def start(self):
        self.thread = Thread(target=self.loop)
        self.thread.start()

    def stop(self):
        self.done = True
        self.thread.join()

    def loop(self):
        self.iterCount = 0
        self.startTime = time()
        while not self.done:
            self.loopBody()
            self.iterCount += 1
        self.stopTime = time()

    @property
    def avePeriod(self):
        return (self.stopTime - self.startTime) / self.iterCount

    @property
    def done(self):
        self.doneLock.acquire()
        val = self._done
        self.doneLock.release()

        return val

    @done.setter
    def done(self, val):
        self.doneLock.acquire()
        self._done = val
        self.doneLock.release()

    # should override loop body
    def loopBody(self):
        pass
