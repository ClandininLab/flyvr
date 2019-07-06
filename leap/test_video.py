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

# Add peak finding
x_peaks = keras.layers.Lambda(tf_find_peaks)(model.output)
model_peaks = keras.models.Model(model.input, x_peaks)



#print(np.shape(image))
#plt.imshow(image)
#plt.show()

# Load video and grab frame to test
vidcap = cv2.VideoCapture(vid_path)
success = True

frame_counter = 0
elapsed_preproc = 0.
elapsed_predict = 0.
elapsed_peak = 0.

while success and frame_counter<1000:
    print(frame_counter)
    frame_counter += 1
    # Grab frame batch

    #try:
    #    frames = next(frame_gen)
    #except:
    #    break
    #frame_counter += len(frames)

    # Preprocessing
    t0 = time()
    success, image = vidcap.read()
    image = np.expand_dims(image, axis=0)
    image = image[:, ::int(1/scale), ::int(1/scale), 0]
    image = np.expand_dims(image, axis=-1)
    image = image.astype("float32") / 255
    elapsed_preproc += time() - t0

    # Inference
    t0 = time()
    confmaps = model.predict(image)
    elapsed_predict += time() - t0

    # Peak finding
    t0 = time()
    peaks, confidences = find_global_peaks(confmaps)
    elapsed_peak += time() - t0

elapsed_total = elapsed_preproc + elapsed_predict + elapsed_peak
print(f"Preprocessing: {frame_counter / elapsed_preproc:.2f} FPS")
print(f"Predict: {frame_counter / elapsed_predict:.2f} FPS")
print(f"Peak finding: {frame_counter / elapsed_peak:.2f} FPS")
print(f"Total: {frame_counter / elapsed_total:.2f} FPS")

#Results with GPU peak finding:
#Preprocessing: 1079.92 FPS
#Predict + peak finding: 125.85 FPS
#Total: 112.72 FPS

# Normal results
# Preprocessing: 1396.47 FPS
# Predict: 173.54 FPS
# Peak finding: 9941.46 FPS
# Total: 152.00 FPS


# Setup video reader
#vid  = video.Video.from_media(vid_path, grayscale=True)

#""" Example of one step of online tracking """
# Preload the video and set up dummy frame acquisition
#frame_gen = frame_generator(vid[:5])

# Grab frame batch
#frames = next(frame_gen)

# Cheap downsampling
# frames = image[:, ::int(1/scale), ::int(1/scale), 0]
# frames = np.expand_dims(frames, axis=-1)
# # Inference
# confmaps = model.predict(frames.astype("float32") / 255)
#
# # Peak finding
# peaks, confidences = find_global_peaks(confmaps)
#
# print("frames:", frames.shape)
# print("confmaps:", confmaps.shape)
# print("peaks:", peaks.shape)
#
# plot_tracked_frame(frames[0], peaks[0])
# plt.show()
