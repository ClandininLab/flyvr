// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef CAMERA_H
#define CAMERA_H

#include <thread>

#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>
#include <opencv2/calib3d/calib3d.hpp>
#include <opencv2/video/video.hpp>
#include <opencv2/xfeatures2d/nonfree.hpp>

// Struct used to keep track of the image displayed in the debug window
enum class DebugImage { Input, Grayscale, Blurred, Threshold, LENGTH };

// Struct used to keep track of fly pose
struct FlyPose{
	double x;
	double y;
	double angle;
	double tstamp;
	bool present;

	// Validity indicator, false initially
	bool valid;

	FlyPose() noexcept : x(0), y(0), angle(0), tstamp(0), present(false), valid(false) {}
};

// High-level thread management for graphics operations
void StartCameraThread(const std::string &outDir);
void StopCameraThread();
void ReadCameraConfig();

// Function to get the fly position within the frame
// Value returned is true if there is a fly
FlyPose GetFlyPose(void);

// Thread used to handle graphics operations
void CameraThread(void);

// Thread used to display images for debugging purposes
void DebugThread(void);
void drawDebugImage(bool flyPresent);

// Image processing routines
void processFrame();
FlyPose locateFly();
bool contourCompare(std::vector<cv::Point> a, std::vector<cv::Point> b);

#endif