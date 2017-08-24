import numpy as np
import cv2

from time import perf_counter
from threading import Lock
from enum import Enum, auto

from service import Service

class CamThread(Service):
    def __init__(self, defaultThresh=150, maxTime=10e-3, logging=True):
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
        self.logging = logging
        if self.logging:
            self.fPtr = open('cam.txt', 'w')
            self.fPtr.write('t,flyPresent,x,y\n')

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
        if self.logging:
            logStr = (str(perf_counter()) + ',' +
                      str(flyData.flyPresent) + ',' +
                      str(flyData.flyX) + ',' +
                      str(flyData.flyY) + '\n')
            self.fPtr.write(logStr)

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

class FlyData:
    def __init__(self, flyX, flyY, flyPresent):
        self.flyX = flyX
        self.flyY = flyY
        self.flyPresent = flyPresent

class FrameData:
    def __init__(self, inFrame, grayFrame, threshFrame, flyContour):
        self.inFrame = inFrame
        self.grayFrame = grayFrame
        self.threshFrame = threshFrame
        self.flyContour = flyContour

class Camera:
    def __init__(self, px_per_m = 14334):
        # Store the number of pixels per meter
        self.px_per_m = px_per_m

        # Open the capture stream
        self.cap = cv2.VideoCapture(0)
        
    def processNext(self, threshold):
        # Capture a single frame
        ret, inFrame = self.cap.read()

        # Convert frame to grayscale
        grayFrame = cv2.cvtColor(inFrame, cv2.COLOR_BGR2GRAY)

        # Threshold image according
        ret, threshFrame = cv2.threshold(grayFrame, threshold, 255, cv2.THRESH_BINARY_INV)

        # Find contours in image
        im2, contours, hierarchy = cv2.findContours(threshFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Set default fly readout
        flyPresent = False
        flyContour = None
        flyX = 0
        flyY = 0

        # If there is a contour, compute its centroid and mark the fly as present
        if len(contours) > 0:
            # Find contour with largest area
            flyContour = max(contours, key = cv2.contourArea)

            # Calculate moments of the largest contour
            M = cv2.moments(flyContour)

            # Calculate centoid of largest contour
            if M['m00'] > 0:
                flyPresent = True
                
                rows, cols = threshFrame.shape
                flyX = (M['m10']/M['m00'] - cols/2)/self.px_per_m 
                flyY = (M['m01']/M['m00'] - rows/2)/self.px_per_m

        # wrap results
        flyData = FlyData(flyPresent=flyPresent,
                          flyX=flyX,
                          flyY=flyY)
        frameData = FrameData(inFrame=inFrame,
                              grayFrame=grayFrame,
                              threshFrame=threshFrame,
                              flyContour=flyContour)

        # Return results
        return flyData, frameData

    def __del__(self):
        # When everything done, release the capture handle
        self.cap.release()
