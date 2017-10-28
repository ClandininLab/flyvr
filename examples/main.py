import cv2
import os
import os.path

from time import strftime, perf_counter
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
from flyvr.display import Stimulus

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

    # keypress generator
    prev_key_set = set()

    # create folder for data
    topdir = r'E:\FlyVR'
    folder = 'exp-'+strftime('%Y%m%d-%H%M%S')
    exp_dir = os.path.join(topdir, folder)
    os.makedirs(exp_dir)
    trial_count = 0
    trial_active = False

    # settings for UI
    tLoop = 1/24
    absJogVel = 0.05

    # Open connection to CNC rig
    print('Homing CNC rig.')
    cnc_home()
    cnc = CncThread()
    cnc.start()

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 66, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)

    # Open connection to camera
    cam = CamThread()
    cam.start()

    # Start tracker thread
    tracker = TrackThread(cncThread=cnc, camThread=cam)
    tracker.start()
    print('Moving CNC rig to center.')
    tracker.move_to_center()

    # main program loop
    while keyboard.Key.esc not in keySet:
        # log start time of loop
        startTime = perf_counter()

        # handle keypress events
        new_keys = keySet - prev_key_set
        prev_key_set = set(keySet)

        # handle start of trials
        if Key.enter in new_keys:
            trial_count += 1
            trial_active = True
            print('Started trial '+str(trial_count))
            folder = 'trial-'+str(trial_count)+'-'+strftime('%Y%m%d-%H%M%S')
            trial_dir = os.path.join(exp_dir, folder)
            os.makedirs(trial_dir)
            cnc.startLogging(os.path.join(trial_dir, 'cnc.txt'))
            cam.startLogging(os.path.join(trial_dir, 'cam.txt'), os.path.join(trial_dir, 'cam.mkv'))
            tracker.startTracking()

        # handle centering
        if KeyCode.from_char('c') in new_keys:
            print('Centering CNC rig.')
            tracker.move_to_center()

        # handle up/down keyboard input
        if Key.up in keySet:
            manVelY = -absJogVel
        elif Key.down in keySet:
            manVelY = +absJogVel
        else:
            manVelY = 0

        # handle left/right keyboard input
        if Key.right in keySet:
            manVelX = +absJogVel
        elif Key.left in keySet:
            manVelX = -absJogVel
        else:
            manVelX = 0

        if ((Key.space in new_keys) or
            (KeyCode.from_char('c') in new_keys) or
            (manVelX != 0) or
            (manVelY != 0)):

            if trial_active:
                print('Stopped trial '+str(trial_count))
                trial_active = False

            cnc.stopLogging()
            cam.stopLogging()
            tracker.stopTracking()

        # create manual control command
        if manVelX != 0 or manVelY != 0:
            manualVelocity = ManualVelocity(velX=manVelX, velY=manVelY)
        else:
            manualVelocity = None

        # issue manual control command
        tracker.manualVelocity = manualVelocity

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
            drawFrame = outFrame.copy()
            if flyContour is not None:
                cv2.drawContours(drawFrame, [flyContour], 0, (0, 255, 0), 2)
                
            # show the image
            cv2.imshow('image', drawFrame)

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
