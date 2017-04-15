// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <fstream>
#include <iostream>
#include <atomic>
#include <SimpleIni.h>

#include "Utility.h"
#include "Camera.h"

using namespace std::chrono;
using namespace cv;

namespace CameraNamespace{
	// File name with configuration parameters
	auto CameraConfigFile = "camera.ini";

	// Frame parameters
	unsigned FrameWidth;
	unsigned FrameHeight;

	// Image processing parameterse
	unsigned LowThresh;
	unsigned HighThresh;
	unsigned BlurSize;
	unsigned MinContour;

	// Scale factors to convert pixels to mm
	double PixelPerMM;

	// Precision of log file
	unsigned LogPrecision;

	// Derived parameters
	unsigned CropAmount, CroppedWidth, CroppedHeight;

	// Target loop duration
	double TargetLoopDuration;

	// Amount of time between debug frames
	double TargetDebugFrameTime;

	// Global variables used to manage access to camera measurement
	std::atomic<FlyPose> g_flyPose;

	// Matrix used to display debug image
	std::mutex debugMutex;
	Mat g_imDebug;

	// Variables used to manage camera thread
	bool killDebug = false;
	bool killCamera = false;
	std::thread cameraThread;

	// Variables used to signal when the camera thread has started up
	BoolSignal readyForCamera;

	// Variables used to hold names of output files
	std::string MovieOutputFile;
	std::string DataOutputFile;
}

using namespace CameraNamespace;

// High-level management of the graphics thread
void StartCameraThread(std::string outDir){
	std::cout << "Starting camera thread.\n";

	// Record names of data file and movie file
	MovieOutputFile = outDir + "/" + "out.avi";
	DataOutputFile = outDir + "/" + "CameraThread.txt"; 

	ReadCameraConfig();
	cameraThread = std::thread(CameraThread);

	// Wait for serial thread to be up and running
	readyForCamera.update(true);
}

// Function to get the fly position within the frame
FlyPose GetFlyPose(void){
	return g_flyPose.load();
}

// Read in the constants for the camera
void ReadCameraConfig(){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(CameraConfigFile);

	// Frame parameters
	FrameWidth = iniFile.GetLongValue("", "frame-width", 200);
	FrameHeight = iniFile.GetLongValue("", "frame-height", 200);

	// Image processing parameterse
	LowThresh = iniFile.GetLongValue("", "low-thresh", 110);
	HighThresh = iniFile.GetLongValue("", "high-thresh", 255);
	BlurSize = iniFile.GetLongValue("", "blur-size", 10);
	MinContour = iniFile.GetLongValue("", "min-contour", 5);

	// Scale factors to convert pixels to mm
	PixelPerMM = iniFile.GetDoubleValue("", "pixel-per-mm", 9.1051);

	// Precision of log file
	LogPrecision = iniFile.GetLongValue("", "log-precision", 8);

	// Precision of log file
	TargetDebugFrameTime = iniFile.GetDoubleValue("", "target-debug-frame-time", 50e-3);
	TargetLoopDuration = iniFile.GetDoubleValue("", "target-loop-duration", 10e-3);

	// Compute derived constants
	CropAmount = BlurSize;
	CroppedWidth = FrameWidth - 2 * CropAmount;
	CroppedHeight = FrameHeight - 2 * CropAmount;
}

// High-level management of the graphics thread
void StopCameraThread(){
	std::cout << "Stopping camera thread.\n";

	// Kill the 3D graphics thread
	killCamera = true;

	// Wait for camera thread to terminate
	cameraThread.join();
}

// Thread used to handle graphics operations
void CameraThread(void){
	// Set up logging
	std::ofstream ofs(DataOutputFile);
	ofs << "flyPresent,";
	ofs << "x (mm),";
	ofs << "y (mm),";
	ofs << "angle (deg),";
	ofs << "timestamp (s)";
	ofs << "\n";
	ofs.precision(LogPrecision);

	// Set up video capture
	std::cout << "Setting up video capture.\n";
	VideoCapture icap(CV_CAP_ANY);
	icap.set(CV_CAP_PROP_FRAME_WIDTH, FrameWidth);
	icap.set(CV_CAP_PROP_FRAME_HEIGHT, FrameHeight);
	
	// Set up video output
	std::cout << "Setting up video output.\n";
	VideoWriter ocap(MovieOutputFile,
		CV_FOURCC('M', 'J', 'P', 'G'),
		1.0/TargetLoopDuration,
		Size(FrameWidth, FrameHeight),
		true);

	// Signal to main thread that camera setup is complete
	std::cout << "Notifying main thread that video capture is set up.\n";
	readyForCamera.update(true);

	TimeManager timeManager("CameraThread");
	timeManager.start();

	TimeManager debugManager("CameraDebug");
	debugManager.start();

	// Launch debug thread
	auto debugThread = std::thread(DebugThread);

	while (!killCamera){
		timeManager.tick();

		// Read image
		Mat inFrame;
		icap.read(inFrame);

		// Write image to file
		ocap.write(inFrame);

		// Copy the debug image over to the debug thread
		{
			std::unique_lock<std::mutex> lck(debugMutex);
			g_imDebug = inFrame.clone();
		}

		// Prepare image for contour search
		Mat outFrame;
		processFrame(inFrame, outFrame);

		// Locate the fly in the frame
		FlyPose flyPose = locateFly(outFrame);

		// Update fly position
		g_flyPose.store(flyPose);

		// Log the fly position
		// Format output data
		std::ostringstream oss;
		oss << flyPose.present << ",";
		oss << std::fixed << flyPose.x << ",";
		oss << std::fixed << flyPose.y << ",";
		oss << std::fixed << flyPose.angle << ",";
		oss << std::fixed << flyPose.tstamp;
		oss << "\n";

		// Write data to file
		ofs << oss.str();

		timeManager.waitUntil(TargetLoopDuration);
	}

	// Kill debug thread
	killDebug = true;
	debugThread.join();
}

void DebugThread(){
	TimeManager debugManager("DebugThread");
	debugManager.start();

	while (!killDebug){
		debugManager.tick();
		Mat imDebug;
		{
			std::unique_lock<std::mutex> lck(debugMutex);
			imDebug = g_imDebug.clone();
		}
		if (imDebug.rows > 0 && imDebug.cols > 0){
			imshow("DebugThread", imDebug);
			waitKey(1);
		}
		debugManager.waitUntil(TargetDebugFrameTime);
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
FlyPose locateFly(const Mat &inFrame){
	// FlyPose to be returned
	FlyPose flyPose;

	// Variables related to contour search
	RotatedRect boundingBox;
	vector<std::vector<cv::Point>> imContours;
	vector<cv::Vec4i> imHierarchy;

	// Find all contours in image
	findContours(inFrame, imContours, imHierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

	// If there are no contours, return
	if (imContours.size() == 0){
		flyPose.tstamp = GetTimeStamp();
		flyPose.valid = true;
		return flyPose;
	}

	// Find the biggest contour
	auto maxElem = std::max_element(imContours.begin(), imContours.end(), contourCompare);

	// If there is no maximum contours, return
	if (maxElem == imContours.end()){
		flyPose.tstamp = GetTimeStamp();
		flyPose.valid = true;
		return flyPose;
	}

	// Check if the biggest contour is large enough
	auto sizeMax = (*maxElem).size();

	if (sizeMax <= MinContour){
		flyPose.tstamp = GetTimeStamp();
		flyPose.valid = true;
		return flyPose;
	}

	// If we reach here, there is a contour large enough for fitEllipse
	boundingBox = fitEllipse(Mat(*maxElem));

	// Compute fly position
	flyPose.x = (boundingBox.center.x - CroppedWidth / 2.0) / PixelPerMM;
	flyPose.y = (boundingBox.center.y - CroppedHeight / 2.0) / PixelPerMM;
	flyPose.angle = boundingBox.angle;
	flyPose.tstamp = GetTimeStamp();
	flyPose.valid = true;

	return flyPose;
}