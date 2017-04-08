// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#pragma once

#include <mutex>
#include <thread>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

namespace CameraConstants{
	// Frame parameters
	const unsigned FrameWidth = 200;
	const unsigned FrameHeight = 200;

	// Image processing parameterse
	const unsigned LowThresh = 110;
	const unsigned HighThresh = 255;
	const unsigned BlurSize = 10;
	const unsigned MinContour = 5;

	// Scale factors to convert pixels to mm
	const double PixelPerMM = 9.1051;

	// Define post-blur cropping
	const unsigned CropAmount = BlurSize;
	const unsigned CroppedWidth = FrameWidth - 2 * CropAmount;
	const unsigned CroppedHeight = FrameHeight - 2 * CropAmount;

	// Precision of log file
	const unsigned LogPrecision = 8;
}

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

// Thread used to handle graphics operations
void CameraThread(void);

// Image processing routines
void processFrame(const cv::Mat &inFrame, cv::Mat &outFrame);
bool locateFly(const cv::Mat &inFrame);
bool contourCompare(std::vector<cv::Point> a, std::vector<cv::Point> b);