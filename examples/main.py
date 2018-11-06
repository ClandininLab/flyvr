import cv2
import os
import platform
import os.path
import itertools

from time import strftime, time, sleep

from flyvr.cnc import CncThread, cnc_home
from flyvr.camera import CamThread
from flyvr.tracker import TrackThread, ManualVelocity
from flyvr.service import Service
from flyvr.mrstim import MrDisplay
import flyvr.gate_control

from flyrpc.launch import launch_server

from threading import Lock

class Smooth:
    def __init__(self, n):
        self.n = n
        self.hist = [0]*n

    def update(self, value):
        self.hist = [float(value)] + self.hist[:-1]
        return sum(self.hist)/self.n

def nothing(x):
    pass

class TrialThread(Service):
    def __init__(self, exp_dir, cam, dispenser, mrstim, loopTime=10e-3, fly_lost_timeout=3, fly_detected_timeout=3,
                 auto_change_rate=None):
        self.trial_count = itertools.count(1)
        self.state = 'startup'
        self.prev_state = 'startup'

        self.cam = cam
        self.dispenser = dispenser
        self.mrstim = mrstim
        self.cnc = None
        self.tracker = None
        self.timer_start = None

        self.exp_dir = exp_dir
        self.fly_lost_timeout = fly_lost_timeout
        self.fly_detected_timeout = fly_detected_timeout
        self.auto_change_rate = auto_change_rate

        # set up access to the thread-ending signal
        self.manualLock = Lock()
        self._manualCmd = None

        self.trialDirLock = Lock()
        self._trial_dir = None

        # start logging to dispenser
        try:
            self.dispenser.start_logging(self.exp_dir)
        except OSError:
            print('Could not set up dispenser logging.')

        # call constructor from parent
        super().__init__(minTime=loopTime, maxTime=loopTime, iter_warn=False)

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

    @property
    def trial_dir(self):
        with self.trialDirLock:
            return self._trial_dir

    def _start_trial(self):
        trial_num = next(self.trial_count)
        print('Started trial ' + str(trial_num))
        folder = 'trial-' + str(trial_num) + '-' + strftime('%Y%m%d-%H%M%S')
        _trial_dir = os.path.join(self.exp_dir, folder)
        os.makedirs(_trial_dir)

        self.cnc.startLogging(os.path.join(_trial_dir, 'cnc.txt'))
        self.cam.startLogging(os.path.join(_trial_dir, 'cam.txt'),
                              os.path.join(_trial_dir, 'cam_compr.mkv'))

        self._trial_dir = _trial_dir
        self.mrstim.nextStim(self._trial_dir)

    def _stop_trial(self):
        print('Stopped trial.')

        self.cnc.stopLogging()
        self.cam.stopLogging()
        self.mrstim.stopStim(self._trial_dir)

        self.tracker.stopTracking()

    def loopBody(self):
        self.mrstim.updateStim(self._trial_dir)

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
                self.state = 'fly detected'
                self.tracker.startTracking()
        elif self.state == 'fly detected':
            if self.manualCmd is not None:
                self.tracker.stopTracking()
                self.prev_state = 'fly detected'
                self.state = 'manual'
                print('** manual **')
            elif (time() - self.timer_start) >= self.fly_detected_timeout:
                print('Fly found!')
                self.tracker.startTracking()
                self._start_trial()
                self.prev_state = 'fly detected'
                self.state = 'run'
                #print('** run **')
            elif not self.cam.flyData.flyPresent:
                print('Fly lost.')
                self.timer_start = time()
                self.prev_state = 'fly detected'
                self.state = 'fly lost'
                self.tracker.stopTracking()
        elif self.state == 'run':
            if self.manualCmd is not None:
                self._stop_trial()
                self.state = 'manual'
                print('** manual **')
            elif not self.cam.flyData.flyPresent:
                print('Fly possibly lost...')
                self.timer_start = time()
                self.prev_state = 'run'
                self.state = 'fly lost'
        elif self.state == 'fly lost':
            if self.manualCmd is not None:
                self._stop_trial()
                self.prev_state = 'fly lost'
                self.state = 'manual'
                print('** manual **')
            elif self.cam.flyData.flyPresent:
                print('Fly located again.')
                self.timer_start = time()
                self.tracker.startTracking()
                if self.prev_state == 'run':
                    self.state = 'run'
                elif self.prev_state == 'fly detected':
                    self.state = 'fly detected'
            elif (time() - self.timer_start) >= self.fly_lost_timeout:
                if self.prev_state == 'run':
                    print('Fly is gone.')
                    self._stop_trial()
                self.tracker.move_to_center()
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
                self.prev_state = 'fly lost'
                self.state = 'started'
        elif self.state == 'manual':
            manualCmd = self.manualCmd

            if manualCmd is None:
                pass
            elif manualCmd[0] == 'start':
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
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
            elif manualCmd[0] == 'release_fly':
                try:
                    self.dispenser.release_fly()
                except OSError:
                    print('Please dispense fly (could not release it automatically)')
            else:
                raise Exception('Invalid manual command.')

            if (manualCmd is not None) and (manualCmd[0] != 'jog'):
                self.resetManual()
        else:
            raise Exception('Invalid state.')

def main():
    # create folder for data
    if platform.system() == 'Windows':
        topdir = r'F:\FlyVR'
    elif platform.system() == 'Linux':
        topdir = '/mnt/fly-data/FlyVR'
    else:
        raise Exception('Invalid platform.')

    # create top-level experiment directory
    folder = 'exp-'+strftime('%Y%m%d-%H%M%S')
    exp_dir = os.path.join(topdir, folder)
    os.makedirs(exp_dir)

    # settings for UI
    tLoop = 1/24
    draw_contour = True
    draw_details = False
    absJogVel = 0.01

    # create the UI
    cv2.namedWindow('image')
    cv2.createTrackbar('threshold', 'image', 236, 254, nothing)
    cv2.createTrackbar('imageType', 'image', 0, 2, nothing)
    cv2.createTrackbar('r_min', 'image', 2, 10, nothing)
    cv2.createTrackbar('r_max', 'image', 8, 10, nothing)

    # loop gain settings
    cv2.createTrackbar('loop_gain', 'image', 100, 750, nothing)

    # Open connection to camera
    cam = CamThread()
    cam.start()

    # Try to connect to the dispenser server
    # ref: https://stackoverflow.com/questions/37863476/why-use-both-os-path-abspath-and-os-path-realpath/40311142
    dispenser = launch_server(flyvr.gate_control)

    #Create Stimulus object
    mrstim = MrDisplay(use_stimuli=True)
    print('mrstim: ', mrstim)

    # Run trial manager
    trialThread = TrialThread(exp_dir=exp_dir, cam=cam, dispenser=dispenser, mrstim=mrstim)
    trialThread.start()

    # Create smoother for fly parameters
    focus_smoother = Smooth(12)
    ma_smoother = Smooth(12)
    MA_smoother = Smooth(12)

    # initialize to no key
    key = -1

    # main program loop
    while key != 27:
        if key == ord('f'):
            draw_details = not draw_details
        if key == ord('d'):
            draw_contour = not draw_contour
        if key == ord('r'):
            cncStatus = trialThread.cnc.status
            if cncStatus is not None:
                posX, posY = cncStatus.posX, cncStatus.posY
                trialThread.tracker.set_center_pos(posX=posX, posY=posY)
            print('new center position set...')
        if key == ord('s'):
            if trialThread.cnc is not None:
                cncStatus = trialThread.cnc.status
                if cncStatus is not None:
                    print('cncX: {}, cncY: {}'.format(cncStatus.posX, cncStatus.posY))

        # manual control options
        if key == 32:
            trialThread.manual('stop')
        if key == 13:
            trialThread.manual('start')
        if key == ord('c'):
            trialThread.manual('center')
        if key == ord('n'):
            dispenser.open_gate()
        if key == ord('m'):
            dispenser.close_gate()
        if key == ord('o'):
            dispenser.calibrate_gate()

        # handle up/down keyboard input
        if key == 56:
            manVelY = +absJogVel
        elif key == 50:
            manVelY = -absJogVel
        else:
            manVelY = 0

        # handle left/right keyboard input
        if key == 54:
            manVelX = -absJogVel
        elif key == 52:
            manVelX = +absJogVel
        else:
            manVelX = 0

        if (manVelX != 0) or (manVelY != 0):
            trialThread.manual('jog', manVelX, manVelY)
        else:
            manualCmd = trialThread.manualCmd
            if (manualCmd is not None) and manualCmd[0] == 'jog':
                trialThread.manual('nojog')

        # handle aspect ratios
        r_min=cv2.getTrackbarPos('r_min', 'image')
        r_max=cv2.getTrackbarPos('r_max', 'image')
        cam.cam.r_min = r_min/10.0
        cam.cam.r_max = r_max/10.0

        # read out tracker settings
        loop_gain = 0.1 * cv2.getTrackbarPos('loop_gain', 'image')
        if trialThread.tracker is not None:
            # check needed since tracker may not have been initialized yet
            trialThread.tracker.a = loop_gain

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

            # compute focus if needed
            if draw_details:
                flyData = cam.flyData
                if (flyData is not None) and flyData.flyPresent:
                    # compute center of region to use for focus calculation
                    rows, cols = frameData.grayFrame.shape
                    bufX = 50
                    bufY = 50
                    flyX_px = min(max(int(round(flyData.flyX_px)), bufX), cols - bufX)
                    flyY_px = min(max(int(round(flyData.flyY_px)), bufY), rows - bufY)

                    # select region to be used for focus calculation
                    focus_roi = frameData.grayFrame[flyY_px - bufY: flyY_px + bufY,
                                                    flyX_px - bufX: flyX_px + bufX]

                    # compute focus figure of merit
                    focus = focus_smoother.update(cv2.Laplacian(focus_roi, cv2.CV_64F).var())
                    focus_str = 'focus: {0:.3f}'.format(focus)

                    # display focus information
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    x0 = 0
                    y0 = 25
                    dy = 50
                    cv2.putText(drawFrame, focus_str, (x0, y0), font, 1, (0, 0, 0))

                    # display minor/major axis information
                    ma = ma_smoother.update(flyData.ma)
                    MA = MA_smoother.update(flyData.MA)
                    r = ma/MA
                    ellipse_str = '{:.1f}, {:.1f}, {:.3f}'.format(1e3*ma, 1e3*MA, r)
                    cv2.putText(drawFrame, ellipse_str, (x0, y0+dy), font, 1, (0, 0, 0))

            # show the image
            cv2.imshow('image', drawFrame)

        # display image
        key = cv2.waitKey(int(round(1e3*tLoop)))
        if (key != -1):
            print('key: {}'.format(key))

    # stop the trial thread manager
    trialThread.stop()

    # stop camera thread
    cam.stop()
    print('Camera FPS: ', 1/cam.avePeriod)

    # close UI window
    cv2.destroyAllWindows()
        
if __name__ == '__main__':
    main()
