from time import time, sleep
from warnings import warn
from threading import Thread, Event

class Service:
    def __init__(self, minTime=None, maxTime=None, iter_warn=True):
        # set up minimum and maximum loop times
        self.minTime = minTime
        self.maxTime = maxTime
        self.iter_warn = iter_warn

        # check that the loop time limits make sense
        if ((self.minTime is not None) and
            (self.maxTime is not None) and
            (self.maxTime < self.minTime)):
            raise Exception('Invalid loop time limits.')

        # set up access to the thread-ending signal
        self.done = Event()

    def start(self):
        self.thread = Thread(target=self.loop)
        self.thread.start()

    def stop(self):
        self.done.set()
        self.thread.join()

    def loop(self):
        # initialize the loop iteration counter
        self.iterCount = 0

        # record service starting time
        self.startTime = time()

        # main logic of loop control
        loopStart = time()
        while not self.done.is_set():
            # run the loop body and measure how long it takes
            self.loopBody()
            loopStop = time()

            # if the loop body finished too early, delay until
            # the minimum loop time passes.  otherwise, if the loop
            # time is too long, issue a warning

            dt = loopStop - loopStart
            loopStart = loopStop

            if (self.minTime is not None) and (dt < self.minTime):
                sleep(self.minTime - dt)

            if (self.iter_warn) and (self.maxTime is not None) and (dt > self.maxTime):
                #print('Slow iteration: {} ({:0.1f} ms)'.format(self.__class__.__name__, dt*1e3))
                pass

            # increment the loop iteration counter
            self.iterCount += 1

        # record service stopping time
        self.stopTime = time()

    @property
    def avePeriod(self):
        return (self.stopTime - self.startTime) / self.iterCount

    # subclasses should override loop body
    def loopBody(self):
        pass
