import numpy as np
import cv2

import os.path

def main():
    folder = r'E:\FlyVR\exp-20171031-214433\trial-10-20171031-222302'
    os.chdir(folder)

    # read measured frame times
    meas_times = np.genfromtxt('cam.txt', delimiter=',', skip_header=1, usecols=(0,))
    meas_times = meas_times - meas_times[0]

    fps = 20
    #fps = 1/np.median(np.diff(meas_times))
    #print(fps)

    # calculate frame times
    # todo: optimize search if speed is an issue
    frame_times = np.arange(0, meas_times[-1], 1/fps)
    frame_idx = np.zeros(len(frame_times))
    for k in range(len(frame_times)):
        frame_idx[k] = np.abs(meas_times - frame_times[k]).argmin()

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