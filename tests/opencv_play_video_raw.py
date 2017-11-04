import numpy as np
import cv2

import os.path

def main():
    folder = r'E:\FlyVR\exp-20171031-214433\trial-12-20171031-224830'
    os.chdir(folder)

    # set up video reading
    vid_file = 'cam.mkv'
    cap = cv2.VideoCapture(vid_file)

    # set up video writing
    compr_file = 'compr_file.avi'
    fourcc = cv2.VideoWriter_fourcc('M', 'P', 'E', 'G')
    out = cv2.VideoWriter(compr_file, fourcc, 124.0, (100,100))

    # loop through video writing all frames
    while(cap.isOpened()):
        ret, frame = cap.read()

        if ret:
            out.write(frame)
        else:
            break

    # release file I/O
    cap.release()
    out.release()

if __name__=='__main__':
    main()