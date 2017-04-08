// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <fstream>

#include "Camera.h"

using namespace std::chrono;
using namespace cv;
using namespace CameraConstants;

// Global variables used to manage access to camera measurement
std::mutex g_cameraMutex;
CamPose g_camPose;

// Variables used to manage camera thread
bool killCamera = false;
std::thread cameraThread;

// High-level management of the graphics thread
void StartCameraThread(){
	cameraThread = std::thread(CameraThread);
}

// High-level management of the graphics thread
void StopCameraThread(){
	// Kill the 3D graphics thread
	killCamera = true;

	// Wait for camera thread to terminate
	cameraThread.join();
}

// Thread used to handle graphics operations
void CameraThread(void){
	// Set up logging
	std::ofstream ofs("CameraThread.txt");
	ofs << "x (mm),";
	ofs << "y (mm),";
	ofs << "angle (deg),";
	ofs << "timestamp (s)";
	ofs << "\r\n";
	ofs.precision(LogPrecision);

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY);
	cap.set(CV_CAP_PROP_FRAME_WIDTH, FrameWidth);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, FrameHeight);

	while (!killCamera){
		// Read image
		Mat inFrame;
		cap.read(inFrame);

		// Prepare image for contour search
		Mat outFrame;
		processFrame(inFrame, outFrame);

		// Locate the fly in the frame
		bool flyFound = locateFly(outFrame);

		// Log the fly position
		if (flyFound){
			// Get the time stamp
			auto tstamp = duration<double>(high_resolution_clock::now().time_since_epoch()).count();

			// Write data to file
			ofs << std::fixed << g_camPose.x << ",";
			ofs << std::fixed << g_camPose.y << ",";
			ofs << std::fixed << g_camPose.angle << ",";
			ofs << std::fixed << tstamp;
			ofs << "\r\n";
		}
	}
}

void processFrame(const Mat &inFrame, Mat &outFrame){
	// Convert to grayscale
	cvtColor(inFrame, outFrame, CV_BGR2GRAY);

	// Blur the image to reduce noise
	blur(outFrame, outFrame, Size(BlurSize, BlurSize));

	// Crop the image to remove edge effects of blurring
	outFrame = outFrame(Rect(CropAmount, CropAmount, CroppedWidth, CroppedHeight));

	// Threshold image to produce black-and-white result
	threshold(outFrame, outFrame, LowThresh, HighThresh, THRESH_BINARY_INV);
}

// Comparison function for contour sizes
bool contourCompare(vector<Point> a, vector<Point> b) {
	return a.size() < b.size();
}

// Locate the fly as the biggest contour in the image
bool locateFly(const Mat &inFrame){
	// Variables related to contour search
	RotatedRect boundingBox;
	vector<std::vector<cv::Point>> imContours;
	vector<cv::Vec4i> imHierarchy;

	// Find all contours in image
	findContours(inFrame, imContours, imHierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

	// Find the biggest contour
	auto maxElem = std::max_element(imContours.begin(), imContours.end(), contourCompare);

	// Check if the biggest contour is large enough
	auto sizeMax = (*maxElem).size();
	if (sizeMax > MinContour){
		boundingBox = fitEllipse(Mat(*maxElem));

		// Compute fly position
		double x = (boundingBox.center.x - CroppedWidth / 2.0) / PixelPerMM;
		double y = (boundingBox.center.y - CroppedHeight / 2.0) / PixelPerMM;
		double angle = boundingBox.angle;

		{
			// Acquire lock for image processing information
			std::unique_lock<std::mutex> lck{ g_cameraMutex };

			// Update shared position
			g_camPose.x = x;
			g_camPose.y = y;
			g_camPose.angle = angle;
		}

		return true;
	}
	else {
		return false;
	}
}