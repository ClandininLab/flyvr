import cv2
import os
import os.path
import itertools

from time import strftime, perf_counter, time, sleep
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
from flyvr.display import Stimulus
from flyvr.service import Service

from threading import Lock

def nothing(x):
    pass

class TrialThread(Service):
    def __init__(self, exp_dir, cam, loopTime=10e-3, fly_lost_timeout=1, fly_found_timeout=1):
        self.trial_count = itertools.count(1)
        self.state = 'startup'

        self.cam = cam
        self.cnc = None
        self.tracker = None
        self.timer_start = None

        self.exp_dir = exp_dir
        self.fly_lost_timeout = fly_lost_timeout
        self.fly_found_timeout = fly_found_timeout

        # set up access to the thread-ending signal
        self.manualLock = Lock()
        self._manualCmd = None

        # call constructor from parent
        super().__init__(minTime=loopTime, maxTime=loopTime)

    @property
    def manualCmd(self):
        with self.manualLock:
            return self._manualCmd

    def resetManual(self):
        with self.manualLock:
            self._manualCmd = None

    def manual(self, *args):
        with self.manualLock:
            self._manualCmd = args

    def stop(self):
        super().stop()
        self.tracker.stop()
        self.cnc.stop()

    def _start_trial(self):
        trial_num = next(self.trial_count)
        print('Started trial ' + str(trial_num))
        folder = 'trial-' + str(trial_num) + '-' + strftime('%Y%m%d-%H%M%S')
        trial_dir = os.path.join(self.exp_dir, folder)
        os.makedirs(trial_dir)
        self.cnc.startLogging(os.path.join(trial_dir, 'cnc.txt'))
        self.cam.startLogging(os.path.join(trial_dir, 'cam.txt'), os.path.join(trial_dir, 'cam.mkv'))

    def _stop_trial(self):
        print('Stopped trial.')

        self.cnc.stopLogging()
        self.cam.stopLogging()
        self.tracker.stopTracking()

    def loopBody(self):
        if self.state == 'startup':
            print('** startup **')

            # Open connection to CNC rig
            cnc_home()
            self.cnc = CncThread()
            self.cnc.start()
            sleep(0.1)

            # Start tracker thread
            self.tracker = TrackThread(cncThread=self.cnc, camThread=self.cam)
            self.tracker.start()
            self.tracker.move_to_center()

            # go to the manual control state
            self.resetManual()
            self.state = 'manual'
            print('** manual **')
        elif self.state == 'started':
            if self.manualCmd is not None:
                self.state = 'manual'
                print('** manual **')
            elif self.cam.flyData.flyPresent:
                print('Fly possibly found...')
                self.timer_start = time()
                self.state = 'fly_found'
                print('** fly_found **')
                self.tracker.startTracking()
        elif self.state == 'fly_found':
            if self.manualCmd is not None:
                self.tracker.stopTracking()
                self.state = 'manual'
                print('** manual **')
            elif not self.cam.flyData.flyPresent:
                print('Fly lost.')
                self.state = 'started'
                print('** started **')
                self.tracker.stopTracking()
                self.tracker.move_to_center()
            elif (time() - self.timer_start) >= self.fly_found_timeout:
                print('Fly found.')
                self._start_trial()
                self.state = 'run'
                print('** run **')
        elif self.state == 'run':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif not self.cam.flyData.flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.state = 'fly_lost'
                print('** fly_lost **')
        elif self.state == 'fly_lost':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif self.cam.flyData.flyPresent:
                print('Fly located again.')
                self.state = 'run'
                print('** run **')
            elif (time() - self.timer_start) >= self.fly_lost_timeout:
                print('Fly lost.')
                self._stop_trial()
                self.tracker.move_to_center()
                self.state = 'started'
                print('** started **')
        elif self.state == 'manual':
            manualCmd = self.manualCmd

            if manualCmd is None:
                pass
            elif manualCmd[0] == 'start':
                self.state = 'started'
                print('** started **')
            elif manualCmd[0] == 'stop':
                print('** manual: stop **')
            elif manualCmd[0] == 'center':
                print('** manual: center **')
                self.tracker.move_to_center()
            elif manualCmd[0] == 'nojog':
                print('** manual: nojog **')
                self.tracker.manualVelocity = None
            elif manualCmd[0] == 'jog':
                manualVelocity = ManualVelocity(velX=manualCmd[1], velY=manualCmd[2])
                self.tracker.manualVelocity = manualVelocity
            else:
                raise Exception('Invalid manual command.')

            if (manualCmd is not None) and (manualCmd[0] != 'jog'):
                self.resetManual()
        else:
            raise Exception('Invalid state.')

def main():
    # handler for key events
    keySet = set()
    def on_press(key):
        keySet.add(key)
    def on_release(key):
        keySet.remove(key)
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    prev_key_set = set()

    # create folder for data
    topdir = r'E:\FlyVR'
    folder = 'exp-'+strftime('%Y%m%d-%H%M%S')
    exp_dir = os.path.join(topdir, folder)
    os.makedirs(exp_dir)

    # settings for UI
    tLoop = 1/24
    draw_contour = True
    absJogVel = 0.05

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 66, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 2, 2, nothing)

    # Open connection to camera
    cam = CamThread()
    cam.start()

    # Run trial manager
    trialThread = TrialThread(exp_dir=exp_dir, cam=cam)
    trialThread.start()

    # main program loop
    while keyboard.Key.esc not in keySet:
        # handle keypress events
        new_keys = keySet - prev_key_set
        prev_key_set = set(keySet)

        if KeyCode.from_char('d') in new_keys:
            draw_contour = not draw_contour
        if KeyCode.from_char('s') in new_keys:
            if trialThread.cnc is not None:
                cncStatus = trialThread.cnc.status
                if cncStatus is not None:
                    print('cncX: {}, cncY: {}'.format(cncStatus.posX, cncStatus.posY))

        # manual control options
        if Key.space in new_keys:
            trialThread.manual('stop')
        if Key.enter in new_keys:
            trialThread.manual('start')
        if KeyCode.from_char('c') in new_keys:
            trialThread.manual('center')

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

        if (manVelX != 0) or (manVelY != 0):
            trialThread.manual('jog', manVelX, manVelY)
        else:
            manualCmd = trialThread.manualCmd
            if (manualCmd is not None) and manualCmd[0] == 'jog':
                trialThread.manual('nojog')

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
            if draw_contour and (flyContour is not None):
                cv2.drawContours(drawFrame, [flyContour], 0, (0, 255, 0), 2)
                
            # show the image
            cv2.imshow('image', drawFrame)

        # display image
        cv2.waitKey(int(round(1e3*tLoop)))

    # stop the trial thread manager
    trialThread.stop()

    # stop camera thread
    cam.stop()
    print('Camera FPS: ', 1/cam.avePeriod)

    # close UI window
    cv2.destroyAllWindows()

    # close the keyboard listener
    listener.stop()
        
if __name__ == '__main__':
    main()