import numpy as np
import cv2

import os.path

def main():
    folder = r'E:\FlyVR\exp-20171027-173629\trial-1-20171027-173809'
    cam_data_file = 'cam.txt'

    jumpThresh=160

    angles = []
    with open(os.path.join(folder, cam_data_file), 'r') as f:
        for k, line in enumerate(f):
            if k==0:
                continue
            angle = float(line.split(',')[-1])

            if len(angles) == 0:
                angles.append(angle)
                continue

            prevAngle = angles[-1]
            while angle-prevAngle > jumpThresh:
                angle -= 180
            while prevAngle-angle > jumpThresh:
                angle += 180
            angles.append(angle)

    angles = np.array(angles)

    vid_file = 'cam.mkv'

    cap = cv2.VideoCapture(os.path.join(folder, vid_file))

    #fourcc = cv2.VideoWriter_fourcc('M', 'P', 'E', 'G')
    fourcc = 0
    compr_file = 'compr_file.mkv'
    out = cv2.VideoWriter(os.path.join(folder, compr_file), fourcc, 20.0, (50, 80))

    frameCount = 0

    while(cap.isOpened()):
        _, frame = cap.read()

        if frameCount % 120 == 0:
            print(frameCount)

        if (frame is None) or (frame.size == 0):
            break

        rows, cols, _ = frame.shape
        M = cv2.getRotationMatrix2D((cols//2, rows//2), angles[frameCount], 1)
        rot_img = cv2.warpAffine(frame, M, (cols, rows), flags = cv2.INTER_CUBIC)
        rot_img = rot_img[rows//2-40:rows//2+40, cols//2-25:cols//2+25]

        frameCount += 1

        cv2.imshow('image', rot_img)

        #out.write(rot_img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print(frameCount)

    cap.release()
    cv2.destroyAllWindows()

if __name__=='__main__':
    main()