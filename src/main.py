import cv2
import os

from time import strftime, sleep, perf_counter
from math import ceil
from warnings import warn
from pynput import keyboard

from cnc import CncThread
from camera import CamThread
from tracker import TrackThread, ManualControl

def nothing(x):
    pass

def main():
    # handler for key events
    keySet = set()
    def on_press(key):
        keySet.add(key)
    def on_release(key):
        keySet.remove(key)
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    # create folder for data
    folderName = strftime("%Y%m%d-%H%M%S")
    os.makedirs(folderName)
    os.chdir(folderName)
    
    # settings for UI
    tLoop = 1/24
    absJogVel = 0.05

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 35, 254, nothing)
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

    # main program loop
    while keyboard.Key.esc not in keySet:
        # log start time of loop
        startTime = perf_counter()

        # handle up/down keyboard input
        if keyboard.Key.up in keySet:
            velX = +absJogVel
        elif keyboard.Key.down in keySet:
            velX = -absJogVel
        else:
            velX = 0

        # handle left/right keyboard input
        if keyboard.Key.right in keySet:
            velY = +absJogVel
        elif keyboard.Key.left in keySet:
            velY = -absJogVel
        else:
            velY = 0

        # create manual control command
        if velX != 0 or velY != 0:
            manualControl = ManualControl(velX=velX, velY=velY)
        else:
            manualControl = None

        # issue manual control command
        tracker.manualControl = manualControl
        
        # compute new thresholds
        threshTrack = cv2.getTrackbarPos('threshold', 'image')
        threshold = threshTrack + 1

        # issue threshold command
        cam.threshold = threshold

        # determine the type of image that should be displayed
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

        # display image
        cv2.waitKey(round(1e3*tLoop))

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

    # close the keyboard listener
    listener.stop()
        
if __name__ == '__main__':
    main()
