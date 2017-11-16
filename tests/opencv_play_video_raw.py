from scipy.interpolate import interp1d
import numpy as np
import cv2

import os.path

def main():
    folder = r'E:\FlyVR\exp-20171031-214433\trial-18-20171031-232610'
    os.chdir(folder)

    # read measured frame times
    meas_times = np.genfromtxt('cam.txt', delimiter=',', skip_header=1, usecols=(0,))
    meas_times = meas_times - meas_times[0]

    fps = 20
    #fps = 1/np.median(np.diff(meas_times))

    # calculate frame times
    frame_times = np.arange(0, meas_times[-1], 1/fps)
    frame_idx = interp1d(meas_times, np.arange(len(meas_times)), kind='nearest', assume_sorted=True)(frame_times)

    # set up video reading
    vid_file = 'cam.mkv'
    cap = cv2.VideoCapture(vid_file)

    # set up video writing
    compr_file = 'compr_file.avi'
    fourcc = cv2.VideoWriter_fourcc('D', 'I', 'V', 'X')
    out = cv2.VideoWriter(compr_file, fourcc, fps, (100,100))

    # loop through video writing all frames
    meas_idx = 0
    ret, frame = cap.read()
    for i in frame_idx:
        while i != meas_idx:
            ret, frame = cap.read()
            meas_idx += 1
        out.write(frame)

    # release file I/O
    cap.release()
    out.release()

if __name__=='__main__':
    main()