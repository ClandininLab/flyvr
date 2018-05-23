import cv2
import numpy as np

from math import pi, sqrt
from time import perf_counter
from threading import Lock
import numpy as np

from flyvr.service import Service

class CamThread(Service):
    def __init__(self, defaultThresh=150, maxTime=10e-3, bufX=200, bufY=200):
        # Serial I/O interface to CNC
        self.cam = Camera()

        # Lock for communicating fly pose changes
        self.flyDataLock = Lock()
        self.flyData = None

        # Lock for communicating debugging frame changes
        self.frameDataLock = Lock()
        self.frameData = None
        self.bufX=bufX
        self.bufY=bufY

        # Lock for communicating the threshold
        self.threshLock = Lock()
        self.threshold = defaultThresh

        # File handle for logging
        self.logLock = Lock()
        self.logFile = None
        self.logVideo = None
        self.logFull = None
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
        logState, logFile, logVideo, logFull = self.getLogState()
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


            if frameData.inFrame.shape != 0:
                # write to uncompressed log video
                # reference: http://answers.opencv.org/question/29260/how-to-save-a-rectangular-roi/

                rows, cols, _ =  frameData.inFrame.shape
                flyX_px = min(max(int(round(flyData.flyX_px)), self.bufX), cols - self.bufX)
                flyY_px = min(max(int(round(flyData.flyY_px)), self.bufY), rows - self.bufY)

                roi = frameData.inFrame[flyY_px-self.bufY: flyY_px+self.bufY,
                                        flyX_px-self.bufX: flyX_px+self.bufX,
                                        :]

                logVideo.write(roi)

                # write to compressed video

                logFull.write(frameData.inFrame)

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

    def startLogging(self, logFile, logVideo, logFull):
        with self.logLock:
            # save log state
            self.logState = True

            # close previous log file
            if self.logFile is not None:
                self.logFile.close()

            # close previous log video
            if self.logVideo is not None:
                self.logVideo.release()

            # close previous full log video
            if self.logFull is not None:
                self.logFull.release()

            # open new log file
            self.logFile = open(logFile, 'w')
            self.logFile.write('t,flyPresent,x,y,ma,MA,angle\n')

            # uncompressed cropped video
            fourcc_uncompr = 0
            self.logVideo = cv2.VideoWriter(logVideo, fourcc_uncompr, 124.2, (2*self.bufX, 2*self.bufY))

            # compressed full video
            fourcc_compr = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
            cam_width = int(self.cam.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            cam_height = int(self.cam.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print('cam_width', cam_width)
            print('cam_height', cam_height)
            self.logFull = cv2.VideoWriter(logFull, fourcc_compr, 124.2, (cam_width, cam_height))

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

            # close previous full log video
            if self.logFull is not None:
                self.logFull.release()

    def getLogState(self):
        with self.logLock:
            return self.logState, self.logFile, self.logVideo, self.logFull

class FrameData:
    def __init__(self, inFrame, grayFrame, threshFrame, flyContour):
        self.inFrame = inFrame
        self.grayFrame = grayFrame
        self.threshFrame = threshFrame
        self.flyContour = flyContour

class Ellipse:
    def __init__(self, cx_px, cy_px, cx, cy, ma, MA, angle):
        self.cx_px = cx_px
        self.cy_px = cy_px
        self.cx = cx
        self.cy = cy
        self.ma = ma
        self.MA = MA
        self.angle = angle

    @property
    def area(self):
        return pi*self.ma*self.MA

class FlyData:
    def __init__(self, flyX_px=0, flyY_px=0, flyX=0, flyY=0, ma=0, MA=0, angle=0, flyPresent=False):
        self.flyX_px = flyX_px
        self.flyY_px = flyY_px
        self.flyX = flyX
        self.flyY = flyY
        self.ma = ma
        self.MA = MA
        self.angle = angle
        self.flyPresent = flyPresent

class ImageProcResult:
    def __init__(self, area_px, perim_px, ellipse):
        self.area_px = area_px
        self.perim_px = perim_px
        self.ellipse = ellipse

# Code in progress from laptop work...
# class ImageProcessor:
#     def __init__(self, px_per_m = 8548.96030065, blur_size=11, fly_area=6.486e-6, fly_perim=11.586e-3,
#                  fly_width=1.695e-3, fly_height=4.911e-3, tol=0.35, thresh_level=0.7):
#         # save settings
#         self.px_per_m = px_per_m
#         self.blur_size = blur_size
#         self.fly_area = fly_area
#         self.fly_perim = fly_perim
#         self.fly_width = fly_width
#         self.fly_height = fly_height
#         self.tol = tol
#         self.thresh_level = thresh_level
#
#         # fly bounding dimensions
#         self.fly_max_dim = max(fly_width, fly_height)
#         self.fly_min_dim = min(fly_width, fly_height)
#
#         # estimated fly parameters in pixels
#         self.fly_area_px2 = self.fly_area * (self.px_per_m ** 2)
#         self.fly_perim_px = self.fly_perim * self.px_per_m
#         self.fly_max_dim_px = self.fly_max_dim * self.px_per_m
#         self.fly_min_dim_px = self.fly_min_dim * self.px_per_m
#
#     def matches(self, val, orig):
#         return abs((val-orig)/orig) <= self.tol
#
#     def get_fly(self, inFrame):
#         # get all contours
#         contours = self.get_contours(inFrame)
#
#         # get all flies
#         flyFound = False
#         fly = None
#         for cnt in contours:
#             result = self.cnt2fly(cnt)
#             if result is not None:
#                 if flyFound:
#                     raise Exception('Multiple flies found.')
#                 else:
#                     flyFound = True
#                     fly = result
#
#         # check result
#         if fly is None:
#             raise Exception('No flies found.')
#
#         return fly
#
#     def cnt2fly(self, cnt):
#         if cnt.size <= 5:
#             return None
#
#         area_px = cv2.contourArea(cnt)
#         if not self.matches(area_px, self.fly_area_px2):
#             return None
#
#         perim_px = cv2.arcLength(cnt, True)
#         if not self.matches(perim_px, self.fly_perim_px):
#             return None
#
#         ellipse = cv2.fitEllipse(cnt)
#         (cx, cy), (sx, sy), angle = ellipse
#         if not self.matches(max(sx, sy), self.fly_max_dim_px):
#             return None
#         if not self.matches(min(sx, sy), self.fly_min_dim_px):
#             return None
#
#         return ImageProcResult(area_px=area_px, perim_px=perim_px, ellipse=ellipse)
#
#     def get_contours(self, inFrame):
#         # Convert frame to grayscale
#         _, _, grayFrame = cv2.split(inFrame)
#
#         # Blur frame
#         blurFrame = cv2.GaussianBlur(grayFrame, (self.blur_size, self.blur_size), 0)
#
#         # Threshold frame
#         thresh = int(round(np.mean(blurFrame)*self.thresh_level))
#         _, threshFrame = cv2.threshold(blurFrame, thresh, 255, cv2.THRESH_BINARY_INV)
#
#         # Get contours
#         _, contours, _ = cv2.findContours(threshFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
#
#         return contours

class Camera:
    def __init__(self,
                 px_per_m = 37023.1016957, # calibrated for 2x on 2/6/2018
                 ma_min = 0.4e-3, # m
                 ma_max = 1.5e-3, # m
                 MA_min = 2e-3, # m
                 MA_max = 4e-3, # m
                 r_min = 0.2,
                 r_max = 0.5
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
#        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 275)
#        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 275)

    def flyCandidate(self, ellipse):
        return ((self.ma_min <= ellipse.ma <= self.ma_max) and
                (self.MA_min <= ellipse.MA <= self.MA_max) and
                (self.r_min <= ellipse.ma/ellipse.MA <= self.r_max))

    def processNext(self, threshold):
        # Capture a single frame
        ret, inFrame = self.cap.read()

        # Convert frame to grayscale
        grayFrame = cv2.cvtColor(inFrame, cv2.COLOR_BGR2GRAY)
        grayFrame = cv2.GaussianBlur(grayFrame, (11, 11), 0)

        # Threshold image according
        rel_level = float(threshold)/255
        auto_thresh = int(round(np.mean(grayFrame)*rel_level))
        ret, threshFrame = cv2.threshold(grayFrame, auto_thresh, 255, cv2.THRESH_BINARY_INV)
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
            ellipse = Ellipse(cx_px=cx,
                              cy_px=cy,
                              cx=-(cx-(cols/2.0))/self.px_per_m,
                              cy=-(cy-(rows/2.0))/self.px_per_m,
                              ma=ma/self.px_per_m,
                              MA=MA/self.px_per_m,
                              angle=angle)
            if self.flyCandidate(ellipse):
                results.append((ellipse, cnt))

        # If there is a contour, compute its centroid and mark the fly as present
        if len(results) > 0:
            bestResult = max(results, key=lambda x: x[0].area)

            ellipse = bestResult[0]
            flyData = FlyData(flyX_px=ellipse.cx_px,
                              flyY_px=ellipse.cy_px,
                              flyX=ellipse.cx,
                              flyY=ellipse.cy,
                              ma=ellipse.ma,
                              MA=ellipse.MA,
                              angle=ellipse.angle,
                              flyPresent=True)

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
