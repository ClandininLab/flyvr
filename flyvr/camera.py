import cv2

from math import pi
from time import perf_counter
from threading import Lock

from flyvr.service import Service

class CamThread(Service):
    def __init__(self, defaultThresh=150, maxTime=10e-3):
        # Serial I/O interface to CNC
        self.cam = Camera()

        # Lock for communicating fly pose changes
        self.flyDataLock = Lock()
        self.flyData = None

        # Lock for communicating debugging frame changes
        self.frameDataLock = Lock()
        self.frameData = None

        # Lock for communicating the threshold
        self.threshLock = Lock()
        self.threshold = defaultThresh

        # File handle for logging
        self.logLock = Lock()
        self.logFile = None
        self.logVideo = None
        self.logState = False

        # call constructor from parent        
        super().__init__(maxTime=maxTime)

    # overriding method from parent...
    def loopBody(self):
        # get the threshold setting
        threshold = self.threshold
        
        # read and process frame
        flyData, frameData = self.cam.processNext(threshold=threshold)

        # update fly data variable
        self.flyData = flyData

        # update the debugging frame variable
        self.frameData = frameData

        # log status
        logState, logFile, logVideo = self.getLogState()
        if logState:
            # write to log file
            logStr = (str(perf_counter()) + ',' +
                      str(flyData.flyPresent) + ',' +
                      str(flyData.flyX) + ',' +
                      str(flyData.flyY) + ',' +
                      str(flyData.ma) + ',' +
                      str(flyData.MA) + ',' +
                      str(flyData.angle) + '\n')
            logFile.write(logStr)

            # write to log video
            logVideo.write(frameData.inFrame)

    @property
    def flyData(self):
        with self.flyDataLock:
            return self._flyData

    @flyData.setter
    def flyData(self, val):
        with self.flyDataLock:
            self._flyData = val

    @property
    def frameData(self):
        with self.frameDataLock:
            return self._frameData

    @frameData.setter
    def frameData(self, val):
        with self.frameDataLock:
            self._frameData = val

    @property
    def threshold(self):
        with self.threshLock:
            return self._threshold

    @threshold.setter
    def threshold(self, val):
        with self.threshLock:
            self._threshold = val

    def startLogging(self, logFile, logVideo):
        with self.logLock:
            # save log state
            self.logState = True

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

            # close previous log video
            if self.logVideo is not None:
                self.logVideo.release()

            # open new log file
            self.logFile = open(logFile, 'w')
            self.logFile.write('t,flyPresent,x,y,ma,MA,angle\n')

            # open new log video
            fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
            self.logVideo = cv2.VideoWriter(logVideo, fourcc, 20.0, (640, 480))

    def stopLogging(self):
        with self.logLock:
            # save log state
            self.logState = False

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

            # close previous log video
            if self.logVideo is not None:
                self.logVideo.release()

    def getLogState(self):
        with self.logLock:
            return self.logState, self.logFile, self.logVideo

class FrameData:
    def __init__(self, inFrame, grayFrame, threshFrame, flyContour):
        self.inFrame = inFrame
        self.grayFrame = grayFrame
        self.threshFrame = threshFrame
        self.flyContour = flyContour

class Ellipse:
    def __init__(self, cx, cy, ma, MA, angle):
        self.cx = cx
        self.cy = cy
        self.ma = ma
        self.MA = MA
        self.angle = angle

    @property
    def area(self):
        return pi*self.ma*self.MA

class FlyData:
    def __init__(self, flyX=0, flyY=0, ma=0, MA=0, angle=0, flyPresent=False):
        self.flyX = flyX
        self.flyY = flyY
        self.ma = ma
        self.MA = MA
        self.angle = angle
        self.flyPresent = flyPresent

class Camera:
    def __init__(self,
                 px_per_m = 8548.96030065,
                 ma_min = 0.75e-3, # m
                 ma_max = 3e-3, # m
                 MA_min = 1.5e-3, # m
                 MA_max = 7e-3, # m
                 r_min = 0.1,
                 r_max = 0.7
                 ):
        # Store the number of pixels per meter
        self.px_per_m = px_per_m

        # Compute minimum and maximum area in terms of pixel area
        self.ma_min = ma_min
        self.ma_max = ma_max
        self.MA_min = MA_min
        self.MA_max = MA_max

        self.r_min = r_min
        self.r_max = r_max

        # Open the capture stream
        self.cap = cv2.VideoCapture(0)

    def flyCandidate(self, ellipse):
        return ((self.ma_min <= ellipse.ma <= self.ma_max) and
                (self.MA_min <= ellipse.MA <= self.MA_max) and
                (self.r_min <= ellipse.ma/ellipse.MA <= self.r_max))

    def processNext(self, threshold):
        # Capture a single frame
        ret, inFrame = self.cap.read()

        # Convert frame to grayscale
        grayFrame = cv2.cvtColor(inFrame, cv2.COLOR_BGR2GRAY)

        # Threshold image according
        ret, threshFrame = cv2.threshold(grayFrame, threshold, 255, cv2.THRESH_BINARY_INV)
        rows, cols = threshFrame.shape

        # Find contours in image
        im2, contours, hierarchy = cv2.findContours(threshFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # remove invalid contours
        results = []
        for cnt in contours:
            if len(cnt) < 5:
                continue
            (cx, cy), (d0, d1), angle = cv2.fitEllipse(cnt)
            MA = max(d0, d1)
            ma = min(d0, d1)
            ellipse = Ellipse(cx=((cx-cols)/2.0)/self.px_per_m,
                              cy=((cy-rows)/2.0)/self.px_per_m,
                              ma=ma/self.px_per_m,
                              MA=MA/self.px_per_m,
                              angle=angle)
            if self.flyCandidate(ellipse):
                results.append((ellipse, cnt))

        # If there is a contour, compute its centroid and mark the fly as present
        if len(results) > 0:
            bestResult = max(results, key=lambda x: x[0].area)

            ellipse = bestResult[0]
            flyData = FlyData(flyX=ellipse.cx,
                              flyY=ellipse.cy,
                              ma=ellipse.ma,
                              MA=ellipse.MA,
                              angle=ellipse.angle)

            flyContour = bestResult[1]
        else:
            flyData = FlyData()
            flyContour = None

        # wrap results
        frameData = FrameData(inFrame=inFrame,
                              grayFrame=grayFrame,
                              threshFrame=threshFrame,
                              flyContour=flyContour)

        # Return results
        return flyData, frameData

    def __del__(self):
        # When everything done, release the capture handle
        self.cap.release()
