# ECC vs. Ellipse Method using Synthetic Rotation

import cv2
import matplotlib.pyplot as plt
from time import perf_counter
import numpy as np
import math

# references:
# https://www.learnopencv.com/image-alignment-ecc-in-opencv-c-python/

def process(img, draw=False):
    blur = cv2.blur(img, (15, 15))
    th = int(round(0.7 * np.median(blur)))
    _, thresh = cv2.threshold(blur, th, 255, cv2.THRESH_BINARY_INV)

    im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    if draw:
        plt.imshow(img)
        plt.show()
        plt.imshow(blur)
        plt.show()
        plt.imshow(thresh)
        plt.show()

    return contours

def noisify(frame, amp=1, jitter=1):
    noise = amp*np.random.randn(*frame.shape)

    with_noise = noise + frame.astype(float)
    with_noise = np.clip(with_noise, 0, 255)
    with_noise = with_noise.astype(np.uint8)

    tx = jitter*np.random.randn()
    ty = jitter*np.random.randn()
    M = np.float32([[1, 0, tx], [0, 1, ty]])
    translated = cv2.warpAffine(with_noise, M, frame.shape)

    return translated

def rotate(frame, angle):
    rows, cols = frame.shape
    M = cv2.getRotationMatrix2D((int(cols / 2), int(rows / 2)), angle % 360, 1)
    rotated = cv2.warpAffine(frame, M, frame.shape)

    return rotated

def dist_to_center(c, shape):
    rows, cols = shape
    cx0 = cols/2
    cy0 = rows/2

    M = cv2.moments(c)
    if M['m00'] == 0:
        return float('inf')

    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])

    return math.hypot(cx-cx0, cy-cy0)

def main():
    # testing parameters
    total_a = 200
    sigma_a = 1
    should_draw = False
    tdraw = 42

    # directory names
    infile = 'test_frame.bmp'

    # cropping parameters
    cx0 = 278
    cy0 = 236
    hw = 200

    # ROI size for ECC fit
    roi_x = 50
    roi_y = 50

    ######################
    # main code below
    ######################

    # read image
    frame = cv2.imread(infile, 0)

    # reshape frame to a square
    rows, cols = frame.shape
    frame = frame[cy0-hw:cy0+hw, cx0-hw:cx0+hw]

    # loop storage
    last_roi = None
    ellipse_angles = np.zeros(total_a)
    warp_angles = np.zeros(total_a-1)

    # generate angular positions
    avec = sigma_a*np.random.randn(total_a)

    # profiling
    duration = 0
    runs = 0

    for k in range(total_a):
        rotated = rotate(frame, avec[k])
        img = noisify(rotated)

        if should_draw:
            cv2.imshow('image', img)
            cv2.waitKey(tdraw)

        ### start timer
        tic = perf_counter()
        ###

        # find possible fly contours in image
        contours = process(img)
        assert len(contours) > 0

        # crude selection criteria for fly contour -- just pick the one closest to center
        match = min(contours, key=lambda c: dist_to_center(c, img.shape))

        # crude adjustment of ellipse angle
        (cx, cy), (sx, sy), ellipse_angle = cv2.fitEllipse(match)
        if ellipse_angle > 90:
            ellipse_angle = 180 - ellipse_angle
        else:
            ellipse_angle *= -1

        ellipse_angles[k] = ellipse_angle

        # crop ROI for ECC fitting
        cx = int(round(cx))
        cy = int(round(cy))
        roi = img[cy-roi_y:cy+roi_y, cx-roi_x:cx+roi_x]

        # run ECC fitting algorithm
        if last_roi is not None:
            warp_matrix = np.eye(2, 3, dtype=np.float32)

            try:
                (cc, warp_matrix) = cv2.findTransformECC(roi, last_roi, warp_matrix, cv2.MOTION_EUCLIDEAN)
            except:
                process(img, draw=True)
                raise

            warp_angle = math.degrees(math.atan2(warp_matrix[1,0],warp_matrix[0,0]))
            warp_angles[k-1] = warp_angle

        # save last ROI image
        last_roi = roi

        ### stop timer
        duration += perf_counter() - tic
        runs += 1
        ###

    if should_draw:
        cv2.destroyAllWindows()

    # ellipse fitting error
    ellipse_angles_error = ellipse_angles - avec

    # ECC method error
    warp_angles_error = warp_angles - np.diff(avec)

    print('Standard deviations')
    print('Ellipse: {:0.3} deg'.format(np.std(ellipse_angles_error)))
    print('ECC: {:0.3} deg'.format(np.std(warp_angles_error)))

    print()

    # runtime
    if runs != 0:
        print('Average runtime: {:0.3} ms'.format((duration/runs)*1e3))

    # plot zero-mean versions on same axis
    plt.plot(ellipse_angles_error - np.mean(ellipse_angles_error), label='Ellipse')
    plt.plot(warp_angles_error - np.mean(warp_angles_error), label='ECC')
    plt.xlabel('Sample')
    plt.ylabel('Error (deg)')
    plt.title('Ellipse vs. ECC method')
    plt.legend()
    plt.show()

if __name__ == '__main__':
    main()