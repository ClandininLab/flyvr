// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef CAMERA_H
#define CAMERA_H

#include <mutex>
#include <thread>
#include <condition_variable>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

// Struct used to keep track of fly pose
struct FlyPose{
	double x;
	double y;
	double angle;
	double tstamp;
};

// High-level thread management for graphics operations
void StartCameraThread();
void StopCameraThread();
void ReadCameraConfig();

// Function to get the fly position within the frame
// Value returned is true if there is a fly
bool GetFlyPose(FlyPose &flyPose);

// Thread used to handle graphics operations
void CameraThread(void);

// Image processing routines
void processFrame(const cv::Mat &inFrame, cv::Mat &outFrame);
bool locateFly(const cv::Mat &inFrame, FlyPose &flyPose);
bool contourCompare(std::vector<cv::Point> a, std::vector<cv::Point> b);

#endif