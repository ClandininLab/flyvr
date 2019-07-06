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
#vid_path = "/home/clandininlab/Documents/flyvr/leap/cam_compr.640x480.mp4"


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

class LeapModel:
    def __init__(self):
        # Initialize network
        model_path = "/home/clandininlab/Documents/flyvr/leap/final_model.h5"
        self.model = keras.models.load_model(model_path)

        # Add peak finding
        x_peaks = keras.layers.Lambda(tf_find_peaks)(self.model.output)
        model_peaks = keras.models.Model(self.model.input, x_peaks)

    def find_points(self, frame, scale=0.25):
        # Cheap downsampling
        frame = frame[::int(1 / scale), ::int(1 / scale)]
        frame = frame[:120,:160]
        frame = np.expand_dims(frame, axis=0)
        frame = np.asarray(np.expand_dims(frame, axis=-1))
        print('frame shape: {}'.format(frame.shape))

        # Inference
        #with tf.Graph().as_default() as graph:

        #with self.graph.as_default():
        confmaps = self.model.predict(frame.astype("float32") / 255)


        # Peak finding
        peaks, confidences = find_global_peaks(confmaps)
        fly_points = FlyPoints(peaks, confidences, scale)
        return fly_points

class FlyPoints:
    def __init__(self, peaks, confidences, scale):
        threshold = 0.5
        self.body = tuple([int(i * 1/scale) for i in peaks[0,0,:]])
        self.head = tuple([int(i * 1/scale) for i in peaks[0,1,:]])
        if confidences[0,0] > threshold:
            self.fly_present = True
        else:
            self.fly_present = False