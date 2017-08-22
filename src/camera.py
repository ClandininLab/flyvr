import numpy as np
import cv2

from threading import Lock
from enum import Enum, auto

from service import Service

class CamThread(Service):
    def __init__(self, defaultThresh=21):
        # Serial I/O interface to CNC
        self.cam = Camera()

        # Lock for communicating measurement changes from camera
        self.statusLock = Lock()
        self.status = None

        # Lock for communicating the threshold
        self.threshLock = Lock()
        self.threshold = defaultThresh

        # Lock for communicating the image type
        self.typeLock = Lock()
        self.imageType = ImageType.RAW

        # call constructor from parent        
        super().__init__()

    # overriding method from parent...
    def loopBody(self):
        # get the threshold setting
        threshold = self.threshold

        # get the image type setting
        imageType = self.imageType
        
        # read and process frame
        status = self.cam.getFlyPos(threshold=threshold, imageType=imageType)

        # update status variable
        self.status = status

    @property
    def status(self):
        with self.statusLock:
            return self._status

    @status.setter
    def status(self, val):
        with self.statusLock:
            self._status = val

    @property
    def threshold(self):
        with self.threshLock:
            return self._threshold

    @threshold.setter
    def threshold(self, val):
        with self.threshLock:
            self._threshold = val

    @property
    def imageType(self):
        with self.typeLock:
            return self._imageType

    @imageType.setter
    def imageType(self, val):
        with self.typeLock:
            self._imageType = val

class CamData:
    def __init__(self, flyX, flyY, flyPresent=False, outFrame=None, flyContour=None):
        self.flyX = flyX
        self.flyY = flyY
        self.flyPresent = flyPresent
        self.outFrame = outFrame
        self.flyContour = flyContour

class ImageType(Enum):
    RAW = auto()
    GRAY = auto()
    THRESH = auto()

class Camera:
    def __init__(self, px_per_m = 14334):
        # Store the number of pixels per meter
        self.px_per_m = px_per_m

        # Open the capture stream
        self.cap = cv2.VideoCapture(0)
        
    def getFlyPos(self, threshold, imageType):
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
            # Find centroid with largest area
            flyContour = max(contours, key = cv2.contourArea)

            # Calculate moments of the largest contour
            M = cv2.moments(flyContour)

            # Calculate centoid of largest contour
            if M['m00'] > 0:
                flyPresent = True
                
                rows, cols = threshFrame.shape
                flyX = (M['m10']/M['m00'] - cols/2)/self.px_per_m 
                flyY = (M['m01']/M['m00'] - rows/2)/self.px_per_m

        # Select the output image, which is always RGB
        if imageType is ImageType.RAW:
            outFrame = inFrame
        elif imageType is ImageType.GRAY:
            outFrame = cv2.cvtColor(grayFrame, cv2.COLOR_GRAY2BGR)
        elif imageType is ImageType.THRESH:
            outFrame = cv2.cvtColor(threshFrame, cv2.COLOR_GRAY2BGR)
        else:
            raise Exception('Invalid output image type.')

        # Return camera data
        return CamData(flyPresent=flyPresent, flyX=flyX, flyY=flyY, outFrame=outFrame, flyContour=flyContour)

    def __del__(self):
        # When everything done, release the capture handle
        self.cap.release()
