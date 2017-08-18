import numpy as np
import cv2

from threading import Lock

from service import Service

class CamThread(Service):
    def __init__(self):
        # Serial I/O interface to CNC
        self.cam = Camera()

        # Lock for communicating measurement changes from camera
        self.statusLock = Lock()
        self.status = None

        # call constructor from parent        
        super().__init__()

    # overriding method from parent...
    def loopBody(self):        
        # read and process frame
        status = self.cam.getFlyPos()

        # update status variable
        self.status = status

    @property
    def status(self):
        self.statusLock.acquire()
        val = self._status
        self.statusLock.release()

        return val

    @status.setter
    def status(self, val):
        self.statusLock.acquire()
        self._status = val
        self.statusLock.release()

class CamStatus:
    def __init__(self, flyX=0.0, flyY=0.0, flyPresent=False):
        self.flyX = flyX
        self.flyY = flyY
        self.flyPresent = flyPresent

class Camera:
    def __init__(self, px_per_m = 14334):
        # Store the number of pixels per meter
        self.px_per_m = px_per_m

        # Open the capture stream
        self.cap = cv2.VideoCapture(0)

    def getFlyPos(self, threshold=21):
        # Capture a single frame
        ret, inFrame = self.cap.read()

        # Convert frame to grayscale
        grayFrame = cv2.cvtColor(inFrame, cv2.COLOR_BGR2GRAY)

        # Threshold image according to trackbar
        ret, threshFrame = cv2.threshold(grayFrame, threshold, 255, cv2.THRESH_BINARY_INV)

        # Find contours in image
        im2, contours, hierarchy = cv2.findContours(threshFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # If there is a contour, return the centroid of the largest one (by area)
        if len(contours) > 0:
            # Find centroid with largest area
            maxContour = max(contours, key = cv2.contourArea)

            # Calculate moments of the largest contour
            M = cv2.moments(maxContour)

            # Calculate centoid of largest contour
            if float(M['m00']) > 0:                    
                rows, cols = threshFrame.shape
                flyX = ((float(M['m10']) / float(M['m00'])) - float(cols)/2.0)/self.px_per_m 
                flyY = ((float(M['m01']) / float(M['m00'])) - float(rows)/2.0)/self.px_per_m

                return CamStatus(flyX, flyY, True)

        # Otherwise return a result indicating there is not fly
        return CamStatus()

    def __del__(self):
        # When everything done, release the capture
        self.cap.release()
