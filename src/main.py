import cv2
import os

from time import strftime
from math import ceil

from cnc import CncThread
from camera import CamThread
from tracker import TrackThread

def nothing(x):
    pass

def main():
    # create folder for data
    folderName = strftime("%Y%m%d-%H%M%S")
    os.makedirs(folderName)
    os.chdir(folderName)
    
    # settings for UI
    tPer = ceil(1e3/24)

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 150, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)    

    # Open connection to CNC rig
    cnc = CncThread()
    cnc.start()

    # Open connection to camera
    cam = CamThread()
    cam.start()

    # Start tracker thread
    tracker = TrackThread(cncThread=cnc, camThread=cam)
    tracker.start()

    while True:
        # adjust threshold
        threshTrack = cv2.getTrackbarPos('threshold', 'image')
        cam.threshold = threshTrack + 1

        # adjust image type
        typeTrack = cv2.getTrackbarPos('imageType', 'image')
        
        # get raw fly position
        frameData = cam.frameData

        if frameData is not None:
            # get the image to display
            if typeTrack==0:
                outFrame = frameData.inFrame
            elif typeTrack==1:
                outFrame = cv2.cvtColor(frameData.grayFrame, cv2.COLOR_GRAY2BGR)
            elif typeTrack==2:
                outFrame = cv2.cvtColor(frameData.threshFrame, cv2.COLOR_GRAY2BGR)
            else:
                raise Exception('Invalid image type.')

            # get the fly contour
            flyContour = frameData.flyContour

            # draw the fly contour if status available
            if flyContour is not None:
                cv2.drawContours(outFrame, [flyContour], 0, (0, 255, 0), 2)
                
            # show the image
            cv2.imshow('image', outFrame)

        # get user input, wait until next frame
        key = cv2.waitKey(tPer)
        if key==27:
            break

    # stop tracker thread
    tracker.stop()
    print('Tracker interval (ms): ', tracker.avePeriod*1e3)

    # stop camera thread
    cam.stop()
    print('Camera FPS: ', 1/cam.avePeriod)

    # stop CNC thread
    cnc.stop()
    print('CNC interval (ms): ', cnc.avePeriod*1e3)

    # close UI window
    cv2.destroyAllWindows()
        
if __name__ == '__main__':
    main()
