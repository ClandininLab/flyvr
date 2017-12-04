import cv2
from flyvr.camera import ImageProcessor
import matplotlib.pyplot as plt
from time import perf_counter
import numpy as np
from tqdm import tqdm

# modified from: https://www.learnopencv.com/image-alignment-ecc-in-opencv-c-python/



def main(new_rows=1024, new_cols=1024):
    #vidname = 'cammedian_uncompr_dead_fly.mkv'
    #vidname = 'cam_compr_dead_fly.mkv'
    #vidname = 'cam_compr_live_fly.mkv'
    vidname = 'exposure_time_8000us_0dB_gain.avi'

    cap = cv2.VideoCapture(vidname)
    proc = ImageProcessor(blur_size=11, thresh_level=0.7)

    duration = 0

    angles = []

    for runs in tqdm(range(100)):
        # Capture frame-by-frame
        ret, inFrameSmall = cap.read()
        if not ret:
            break

        # pad image to larger size
        inFrame = np.zeros((new_rows, new_cols, 3), np.uint8)
        inFrame[:] = (0, 0, int(round(np.median(inFrameSmall[:, :, 2]))))
        rows, cols, _ = inFrameSmall.shape
        inFrame[:rows-1, :cols-1, :] = inFrameSmall[:rows-1, :cols-1]

        # Convert frame to grayscale
        _, _, grayFrame = cv2.split(inFrame)

        # Blur frame
        blurFrame = cv2.GaussianBlur(grayFrame, (proc.blur_size, proc.blur_size), 0)

        # Threshold frame
        thresh = int(round(np.mean(blurFrame)*proc.thresh_level))
        _, threshFrame = cv2.threshold(blurFrame, thresh, 255, cv2.THRESH_BINARY_INV)

        # Get contours
        _, contours, _ = cv2.findContours(threshFrame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        outFrame = inFrame
        #outFrame = cv2.cvtColor(threshFrame, cv2.COLOR_GRAY2BGR)

        tic = perf_counter()
        try:
            fly = proc.get_fly(inFrame)
        except:
            fly = None
        duration += perf_counter() - tic

        if fly is not None:
            _,  _, angle = fly.ellipse
            angles.append(angle)

            cv2.ellipse(outFrame, fly.ellipse, (0, 255, 0), 2)

        # Display the resulting frame
        cv2.imshow('frame', outFrame)
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    print('average runtime: {:.3} ms (N={})'.format(1e3*(duration/runs), runs))
    print('standard deviation of angle: {:.3} deg'.format(np.std(np.array(angles))))

    #plt.plot(np.array(angles))
    #plt.show()

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()