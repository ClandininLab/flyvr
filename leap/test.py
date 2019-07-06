import matplotlib.pyplot as plt
import numpy as np
import h5py
from time import time
import cv2

import tensorflow as tf
keras = tf.keras # Saves us a dependency :)

#print("GPU:", tf.test.is_gpu_available())

# Installed Cuda and Tensorflow
# https://medium.com/better-programming/install-tensorflow-1-13-on-ubuntu-18-04-with-gpu-support-239b36d29070

#""" Parameters """
vid_path = "/home/clandininlab/Documents/flyvr/leap/cam_compr.640x480.mp4"
model_path = "/home/clandininlab/Documents/flyvr/leap/final_model.h5"
scale = 0.25

#""" Helper functions """

def frame_generator(frames, batch_size=1):
    for frame in frames:
        # Fill up batch buffer
        batch = []
        while len(batch) < batch_size:
            batch.append(frame)

        # Stack into 4-D
        batch = np.stack(batch, axis=0)

        # Adjust for batch_size = 1
        if batch.ndim < 4:
            batch = np.expand_dims(batch, axis=0)

        # Send out batch of images
        yield batch

    # Send last batch if it wasn't complete
    if len(batch) < batch_size:
        yield batch


def find_global_peaks(confmaps):
    # Pre-allocate
    N, H, W, K = confmaps.shape
    peaks = np.full((N, K, 2), np.nan)
    confidences = np.full((N, K), np.nan)

    for n in range(N):
        for k in range(K):
            ind = np.argmax(confmaps[n, ..., k].squeeze())
            r, c = np.unravel_index(ind, (H, W))
            peaks[n, k, :] = [c, r]
            confidences[n, k] = confmaps[n, r, c, k]

    return peaks, confidences


def tf_find_peaks(x):
    """ Finds the maximum value in each channel and returns the location and value.
    Args:
        x: rank-4 tensor (samples, height, width, channels)
    Returns:
        peaks: rank-3 tensor (samples, [x, y, val], channels)
    """

    # Store input shape
    in_shape = tf.shape(x)

    # Flatten height/width dims
    flattened = tf.reshape(x, [in_shape[0], -1, in_shape[-1]])

    # Find peaks in linear indices
    idx = tf.argmax(flattened, axis=1)

    # Convert linear indices to subscripts
    rows = tf.floor_div(tf.cast(idx, tf.int32), in_shape[1])
    cols = tf.floormod(tf.cast(idx, tf.int32), in_shape[1])

    # Dumb way to get actual values without indexing
    vals = tf.reduce_max(flattened, axis=1)

    # Return N x 3 x C tensor
    return tf.stack([
        tf.cast(cols, tf.float32),
        tf.cast(rows, tf.float32),
        vals
    ], axis=1)


def plot_tracked_frame(frame, peaks):
    plt.figure(figsize=(8, 8))
    plt.imshow(frame.squeeze(), cmap="gray")
    if peaks.ndim == 3: peaks = peaks[0]
    plt.scatter(peaks[:, 0], peaks[:, 1], c=np.arange(len(peaks)), vmin=0, vmax=len(peaks) - 1, cmap="RdBu")


def plot_blended_confmaps(frame, confmaps):
    plt.figure(figsize=(8, 8))
    plt.imshow(frame.squeeze(), cmap="gray")

    if confmaps.ndim > 3:
        confmaps = confmaps[0]
    K = confmaps.shape[-1]
    for k in range(K):
        cm = confmaps[:, :, k]
        cm[cm < 0.1] = 0
        plt.imshow(cm + k, vmin=0, vmax=K, cmap="hsv", alpha=0.2)

# Initialize network
model = keras.models.load_model(model_path)
model.summary()

# Load video and grab frame to test
vidcap = cv2.VideoCapture(vid_path)
success = True
counter = 0
image = None
while success and counter < 10:
    last_image = image
    counter += 1
    print(counter)
    success, image = vidcap.read()
image = np.expand_dims(last_image, axis=0)
print(np.shape(image))
#plt.imshow(image)
#plt.show()

# Add peak finding
#x_peaks = keras.layers.Lambda(tf_find_peaks)(model.output)
#model_peaks = keras.models.Model(model.input, x_peaks)

# Setup video reader
#vid  = video.Video.from_media(vid_path, grayscale=True)

#""" Example of one step of online tracking """
# Preload the video and set up dummy frame acquisition
#frame_gen = frame_generator(vid[:5])

# Grab frame batch
#frames = next(frame_gen)

# Cheap downsampling
frames = image[:, ::int(1/scale), ::int(1/scale), 0]
frames = np.asarray(np.expand_dims(frames, axis=-1))
# Inference
print('training frame: {}'.format(frames.shape))
confmaps = model.predict(frames.astype("float32") / 255)

# Peak finding
peaks, confidences = find_global_peaks(confmaps)

print("frames:", frames.shape)
print("confidences:", confidences.shape)
print("confidences:", confidences)
#print("confmaps:", confmaps.shape)
#print("confmaps:", confmaps)
print("peaks:", peaks.shape)
print(peaks)
print(peaks[0,0,:])
frame = frames[0,:,:,0]
print("frame:", frame.shape)
frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
print("frame:", frame.shape)
#plot_blended_confmaps(frames[0], confmaps[0])



point = tuple([int(i) for i in peaks[0,0,:]])
cv2.circle(frame, point, 2, color=(150,150,150),thickness=2, lineType=8, shift=0)
#cv2.line(frame,(0,0),(150,150),(255,255,255),15)
#cv2.circle(frame,(100,63), 55, (0,255,0), -1)

length=30
thickness=3
color=(0, 0, 255)
point=(30,30)
tip=(5,50)
#cv2.arrowedLine(frame, point, tip, color, thickness, tipLength=0.3)


cv2.imshow('image',frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
#plt.imshow(frame)

#plot_tracked_frame(frames[0], peaks[0])
#plt.show()

# With fly:
# confidences: (1, 2)
# confidences: [[ 0.92328268  0.97421455]]

# No fly:
# confidences: [[ 0.00219328  0.00313675]]