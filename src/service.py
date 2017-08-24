from time import perf_counter, sleep
from warnings import warn
from threading import Thread, Lock

class Service:
    def __init__(self, minTime=None, maxTime=None):
        # set up minimum and maximum loop times
        self.minTime = minTime
        self.maxTime = maxTime

        # check that the loop time limits make sense
        if ((self.minTime is not None) and
            (self.maxTime is not None) and
            (self.maxTime < self.minTime)):
            raise Exception('Invalid loop time limits.')

        # set up access to the thread-ending signal
        self.doneLock = Lock()
        self.done = False

    def start(self):
        self.thread = Thread(target=self.loop)
        self.thread.start()

    def stop(self):
        self.done = True
        self.thread.join()

    def loop(self):
        # initialize the loop iteration counter
        self.iterCount = 0

        # record service starting time
        self.startTime = perf_counter()

        # main logic of loop control
        while not self.done:
            # run the loop body and measure how long it takes
            loopStart = perf_counter()
            self.loopBody()
            loopStop = perf_counter()

            # if the loop body finished too early, delay until
            # the minimum loop time passes.  otherwise, if the loop
            # time is too long, issue a warning
            dt = loopStop-loopStart
            if (self.minTime is not None) and (dt < self.minTime):
                sleep(self.minTime - dt)
            elif (self.maxTime is not None) and (dt > self.maxTime):
                warn('Slow iteration: ' + type(self).__name__)

            # increment the loop iteration counter
            self.iterCount += 1

        # record service stopping time
        self.stopTime = perf_counter()

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

    # subclasses should override loop body
    def loopBody(self):
        pass
