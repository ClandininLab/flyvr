// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <fstream>

#include "Camera.h"

using namespace std::chrono;
using namespace cv;
using namespace CameraConstants;

// Global variable declarations
bool g_killCamera = false;
std::mutex g_cameraMutex;
std::thread g_cameraThread;

Mat g_origFrame, g_procFrame;
RotatedRect g_boundingBox;
vector<vector<Point>> g_imContours;
vector<Vec4i> g_imHierarchy;
CamPose g_camPose;

// High-level management of the graphics thread
void StartCameraThread(){
	// Graphics setup
	g_cameraThread = std::thread(CameraThread);
}

void StopCameraThread(){
	// Kill the 3D graphics thread
	g_killCamera = true;

	// Wait for camera thread to terminate
	g_cameraThread.join();
}

// Thread used to handle graphics operations
void CameraThread(void){
	// Set up logging

	std::ofstream ofs("CameraThread.txt");
	ofs << "x (mm),y (mm),angle (deg),timestamp (s)";
	ofs.precision(LogPrecision);

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, FrameWidth);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, FrameHeight);

	while (!g_killCamera){
		// Read image
		cap.read(g_origFrame);

		// Prepare image for contour search
		prepFrame();

		// Locate the fly in the frame
		bool flyFound = locateFly();

		// Log the fly position
		if (flyFound){
			// Get the time stamp
			auto tstamp = duration<double>(high_resolution_clock::now().time_since_epoch()).count();

			// Write data to file
			ofs << g_camPose.x << "," << g_camPose.y << "," << g_camPose.angle << "," << tstamp << "\r\n";
		}
	}
}

void prepFrame(){
	// Convert to grayscale
	cvtColor(g_origFrame, g_procFrame, CV_BGR2GRAY);

	// Blur the image to reduce noise
	blur(g_procFrame, g_procFrame, Size(BlurSize, BlurSize));

	// Crop the image to remove edge effects of blurring
	g_procFrame = g_procFrame(Rect(CropAmount, CropAmount, CroppedWidth, CroppedHeight));

	// Threshold image to produce black-and-white result
	threshold(g_procFrame, g_procFrame, LowThresh, HighThresh, THRESH_BINARY_INV);
}

// Comparison function for contour sizes
bool contourCompare(vector<Point> a, vector<Point> b) {
	return a.size() < b.size();
}

//
bool locateFly(){
	findContours(g_procFrame, g_imContours, g_imHierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

	// Find biggest contour
	auto maxElem = std::max_element(g_imContours.begin(), g_imContours.end(), contourCompare);

	// Check if the biggest contour is large enough
	auto sizeMax = (*maxElem).size();
	if (sizeMax > MinContour){
		g_boundingBox = fitEllipse(Mat(*maxElem));

		// Compute fly position
		double x = (g_boundingBox.center.x - CroppedWidth / 2.0) / PixelPerMM;
		double y = (g_boundingBox.center.y - CroppedHeight / 2.0) / PixelPerMM;
		double angle = g_boundingBox.angle;

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