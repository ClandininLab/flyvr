// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef CAMERA_H
#define CAMERA_H

#include <mutex>
#include <thread>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

// Struct used to keep track of fly pose
struct CamPose{
	double x;
	double y;
	double angle;
};

// Global variables used to manage access to camera measurement
extern std::mutex g_cameraMutex;
extern CamPose g_camPose;

// High-level thread management for graphics operations
void StartCameraThread();
void StopCameraThread();
void ReadCameraConfig();

// Thread used to handle graphics operations
void CameraThread(void);

// Image processing routines
void processFrame(const cv::Mat &inFrame, cv::Mat &outFrame);
bool locateFly(const cv::Mat &inFrame);
bool contourCompare(std::vector<cv::Point> a, std::vector<cv::Point> b);

#endif