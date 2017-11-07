import cv2

from math import ceil

from flyvr.camera import CamThread

def nothing(x):
    pass

def main():
    # settings for UI
    tLoop = 1/24

    # launch the camera processing thread
    camThread = CamThread()
    camThread.start()

    camThread.startLogging('cam.txt', 'cam_uncompr.mkv', 'cam_compr.mkv')

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 122, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)        

    # loop until user presses ESC
    while True:
        # adjust threshold
        threshTrack = cv2.getTrackbarPos('threshold', 'image')
        camThread.threshold = threshTrack + 1

        # adjust image type
        typeTrack = cv2.getTrackbarPos('imageType', 'image')

        frameData = camThread.frameData

        # draw the image if status available
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
            drawFrame = outFrame.copy()
            if flyContour is not None:
                cv2.drawContours(drawFrame, [flyContour], 0, (0, 255, 0), 2)

            # compute focus if needed
            flyData = camThread.flyData
            if (flyData is not None) and flyData.flyPresent:
                # compute center of region to use for focus calculation
                rows, cols = frameData.grayFrame.shape
                bufX = 50
                bufY = 50
                flyX_px = min(max(int(round(flyData.flyX_px)), bufX), cols - bufX)
                flyY_px = min(max(int(round(flyData.flyY_px)), bufY), rows - bufY)

                # select region to be used for focus calculation
                focus_roi = frameData.grayFrame[flyY_px-bufY: flyY_px+bufY,
                                                flyX_px-bufX: flyX_px+bufX]

                # compute focus figure of merit
                focus = cv2.Laplacian(focus_roi, cv2.CV_64F).var()
                focus_str = 'focus: {0:.3f}'.format(focus)

                # display focus information
                font = cv2.FONT_HERSHEY_SIMPLEX
                x0 = 0
                y0 = 25
                dy = 35
                cv2.putText(drawFrame, focus_str, (x0, y0), font, 1, (255, 255, 255))

            # show the image
            cv2.imshow('image', drawFrame)

        # get user input, wait until next frame
        key = cv2.waitKey(round(1e3*tLoop))
        if key==27:
            break        

    # close UI window
    cv2.destroyAllWindows()

    # stop processing frames
    camThread.stop()

    # print out thread information
    print('frames per second:', 1/camThread.avePeriod)
    print('number of iterations:', camThread.iterCount)
    
if __name__=='__main__':
    main()
