import time
import cv2
import numpy as np

from math import ceil

from camera import CamThread, ImageType

def nothing(x):
    pass

def main():
    # settings for UI
    tPer = ceil(1e3/24)
    typeDir = {0: ImageType.RAW, 1: ImageType.GRAY, 2: ImageType.THRESH}

    # launch the camera processing thread
    camThread = CamThread()
    camThread.start()

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 150, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)        

    # loop until user presses ESC
    while True:
        # adjust threshold
        threshTrack = cv2.getTrackbarPos('threshold', 'image')
        camThread.threshold = threshTrack + 1

        # adjust image type
        typeTrack = cv2.getTrackbarPos('imageType', 'image')
        camThread.imageType = typeDir[typeTrack]
        
        # read status
        status = camThread.status

        # draw the image if status available
        if status is not None:
            # draw fly contour if present
            if status.flyPresent:
                cv2.drawContours(status.outFrame, [status.flyContour], 0, (0, 255, 0), 2)
            # show the image
            cv2.imshow('image', status.outFrame)

        # get user input, wait until next frame
        key = cv2.waitKey(tPer)
        if key==27:
            break        

    # close UI window
    cv2.destroyAllWindows()

    # stop processing frames
    camThread.stop()

    # print out thread information
    print('Camera FPS: ', 1/camThread.avePeriod)
    
if __name__=='__main__':
    main()
