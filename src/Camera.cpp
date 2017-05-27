// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <fstream>
#include <iostream>
#include <atomic>
#include <vector>
#include <SimpleIni.h>

#include "Utility.h"
#include "Camera.h"

using namespace std::chrono;
using namespace cv;
using namespace cv::xfeatures2d;

namespace CameraNamespace{
	// File name with configuration parameters
	auto CameraConfigFile = "camera.ini";

	// Frame parameters
	unsigned FrameWidth;
	unsigned FrameHeight;
	unsigned FrameFPS;

	// Image processing parameterse
	std::atomic<unsigned> LowThresh;
	std::atomic<unsigned> HighThresh;
	std::atomic<unsigned> BlurSize;
	std::atomic<unsigned> MinContour;

	// Scale factors to convert pixels to mm
	double PixelPerMM;

	// Precision of log file
	unsigned LogPrecision;

	// Target loop duration
	double TargetLoopDuration;

	// Amount of time between debug frames
	double TargetDebugFrameTime;

	// Use a pre-recorded video
	bool UseRecordedInput;
	std::string RecordedInputFile;

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
	//std::string FlyTemplateFile;
	//std::string FlyMaskFile;

	// Variable used to hold image used for debugging
	std::atomic<DebugImage> debugImage = DebugImage::Input;

	// OpenCV matrices
	Mat inFrame, grayFrame, blurFrame, threshFrame, croppedFrame;
	RotatedRect boundingBox;
	Rect roi;
}

using namespace CameraNamespace;

// High-level management of the graphics thread
void StartCameraThread(const std::string &outDir){
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
	FrameFPS = int((1.0 / TargetLoopDuration) + 1);

	// Precision of log file
	UseRecordedInput = iniFile.GetBoolValue("", "use-recorded-input", false);
	RecordedInputFile = iniFile.GetValue("", "recorded-input-file", "in.avi");
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
	std::cout << "Trying to open camera...";

	VideoCapture icap;
	if (UseRecordedInput) {
		icap = VideoCapture(RecordedInputFile);
	}
	else {
		icap = VideoCapture(CV_CAP_ANY);
	}

	icap.set(CV_CAP_PROP_FRAME_WIDTH, FrameWidth);
	icap.set(CV_CAP_PROP_FRAME_HEIGHT, FrameHeight);
	
	if (icap.isOpened()){
		std::cout << "success.\n";
	} else{
		std::cout << "FAILED.\n";
		throw std::exception("Failed to open camera.");
	}
	
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

	// Launch debug thread
	auto debugThread = std::thread(DebugThread);

	while (!killCamera){
		timeManager.tick();

		// Read image
		bool hasFrame = icap.read(inFrame);

		// Loop video when using recorded input
		if (UseRecordedInput) {
			if (!hasFrame) {
				// Reload file
				icap = VideoCapture(RecordedInputFile);
				continue;
			}
		}
		
		// Write image to file
		ocap.write(inFrame);

		// Prepare image for contour search
		processFrame();

		// Locate the fly in the frame
		FlyPose flyPose = locateFly();

		// Update fly position
		g_flyPose.store(flyPose);

		// Show image on debug window
		drawDebugImage(flyPose.present);

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

	int blur_slider = BlurSize;
	int thresh_slider = LowThresh;
	int debugImage_slider = int((DebugImage)debugImage);
	bool madeTrackbars = false;

	namedWindow("DebugThread", CV_WINDOW_AUTOSIZE);

	while (!killDebug){
		debugManager.tick();

		BlurSize = std::max(blur_slider, 1);
		LowThresh = std::max(thresh_slider, 1);
		debugImage = DebugImage(debugImage_slider);

		Mat imDebug;
		{
			std::unique_lock<std::mutex> lck(debugMutex);
			imDebug = g_imDebug.clone();
		}

		if (imDebug.rows > 0 && imDebug.cols > 0){
			resize(imDebug, imDebug, Size(imDebug.cols * 2, imDebug.rows * 2));
			imshow("DebugThread", imDebug);
			if (!madeTrackbars) {
				madeTrackbars = true;
				createTrackbar("Blur Size", "DebugThread", &blur_slider, 30);
				createTrackbar("Low Threshold", "DebugThread", &thresh_slider, 255);
				createTrackbar("Debug Image", "DebugThread", &debugImage_slider, int(DebugImage::LENGTH) - 1);
			}
			waitKey(1);
		}
		debugManager.waitUntil(TargetDebugFrameTime);
	}
}

void processFrame(){
	// Convert to grayscale
	cvtColor(inFrame, grayFrame, CV_BGR2GRAY);

	// Blur the image to reduce noise
	blur(grayFrame, blurFrame, Size(BlurSize, BlurSize));
	// medianBlur(grayFrame, blurFrame, 2.*std::round((BlurSize + 1.0) / 2.0) - 1);

	// Threshold image to produce black-and-white result
	threshold(blurFrame, threshFrame, LowThresh, HighThresh, THRESH_BINARY_INV);
}

// Comparison function for contour sizes
bool contourCompare(std::vector<Point> a, std::vector<Point> b) {
	return a.size() < b.size();
}

// Locate the fly as the biggest contour in the image
FlyPose locateFly(){
	// Crop the image to remove edge effects of blurring
	int CropAmount = (int)((BlurSize+1)/2.0);
	int CroppedWidth = FrameWidth - 2 * CropAmount;
	int CroppedHeight = FrameHeight - 2 * CropAmount;
	roi = Rect(CropAmount, CropAmount, CroppedWidth, CroppedHeight);
	croppedFrame = threshFrame(roi);

	// FlyPose to be returned
	FlyPose flyPose;

	// Variables related to contour search
	std::vector<std::vector<cv::Point>> imContours;
	std::vector<cv::Vec4i> imHierarchy;

	// Find all contours in image
	findContours(croppedFrame, imContours, imHierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

	// If there are no contours, return
	if (imContours.size() == 0){
		flyPose.tstamp = GetTimeStamp();
		flyPose.present = false;
		flyPose.valid = true;
		return flyPose;
	}

	// Find the biggest contour
	auto maxElem = std::max_element(imContours.begin(), imContours.end(), contourCompare);

	// If there is no maximum contours, return
	if (maxElem == imContours.end()){
		flyPose.tstamp = GetTimeStamp();
		flyPose.present = false;
		flyPose.valid = true;
		return flyPose;
	}

	// Check if the biggest contour is large enough
	auto sizeMax = (*maxElem).size();

	if (sizeMax <= MinContour){
		flyPose.tstamp = GetTimeStamp();
		flyPose.present = false;
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
	flyPose.present = true;
	flyPose.valid = true;

	return flyPose;
}

void drawDebugImage(bool flyPresent) {
	// Acquire lock for g_imDebug
	std::unique_lock<std::mutex> lck(debugMutex);

	// Show the desired debugging image
	if (debugImage == DebugImage::Input) {
		g_imDebug = inFrame.clone();
	}
	else if (debugImage == DebugImage::Grayscale) {
		g_imDebug = grayFrame.clone();
		cvtColor(g_imDebug, g_imDebug, CV_GRAY2BGR);
	}
	else if (debugImage == DebugImage::Blurred) {
		g_imDebug = blurFrame.clone();
		cvtColor(g_imDebug, g_imDebug, CV_GRAY2BGR);
	}
	else if (debugImage == DebugImage::Threshold) {
		g_imDebug = threshFrame.clone();
		cvtColor(g_imDebug, g_imDebug, CV_GRAY2BGR);
	}
	else {
		throw std::exception("Unknown debugImage type.");
	}

	// Draw region of interest (ROI)
	rectangle(g_imDebug, roi, Scalar(0, 0, 255), 1, 8, 0);

	// Draw the fly ellipse if it's present
	if (flyPresent) {
		auto shift = roi.tl();
		auto centerShift = Point2f(boundingBox.center.x + shift.x, boundingBox.center.y + shift.y);
		auto bboxShift = RotatedRect(centerShift, boundingBox.size, boundingBox.angle);
		ellipse(g_imDebug, bboxShift, Scalar(255, 0, 0));
	}
}

//// OLD CODE

// Reference: http://docs.opencv.org/3.2.0/de/da9/tutorial_template_matching.html
/*
FlyPose locateFly() {
Mat result;

double maxVal = 0;
for (double angle = )
matchTemplate(grayFrame, flyTemplate, result, CV_TM_SQDIFF, flyMask);
double minVal; double maxVal; Point minLoc; Point maxLoc;
minMaxLoc(result, &minVal, &maxVal, &minLoc, &maxLoc, Mat());
Point matchLoc;
matchLoc = minLoc;

{
std::unique_lock<std::mutex> lck(debugMutex);
//g_imDebug = result.clone();
g_imDebug = grayFrame.clone();
rectangle(g_imDebug, matchLoc, Point(matchLoc.x + flyTemplate.cols, matchLoc.y + flyTemplate.rows), Scalar::all(0), 2, 8, 0);
}

FlyPose toReturn;
return toReturn;
}
*/

/*
FlyPose locateFly() {
Mat result = estimateRigidTransform(flyTemplate, grayFrame, false);

// Draw image for debug purposes
{
std::unique_lock<std::mutex> lck(debugMutex);
g_imDebug = flyTemplate.clone();
}

std::cout << result;

FlyPose toReturn;
return toReturn;
}
*/

// Reference: http://docs.opencv.org/2.4/doc/tutorials/features2d/feature_homography/feature_homography.html
/*
FlyPose locateFly() {
std::vector<KeyPoint> flyKeypoints, imgKeypoints;
Mat flyDescriptors, imgDescriptors;

flyDetector = SURF::create(MinHessian);

flyDetector->detectAndCompute(flyTemplate, noArray(), flyKeypoints, flyDescriptors);
flyDetector->detectAndCompute(grayFrame, noArray(), imgKeypoints, imgDescriptors);

FlannBasedMatcher matcher;
std::vector< DMatch > matches;
matcher.match(flyDescriptors, imgDescriptors, matches);

//-- Localize the object
std::vector<Point2f> flyMatchPoints;
std::vector<Point2f> imgMatchPoints;

for (int i = 0; i < matches.size(); i++)
{
//-- Get the keypoints from the good matches
flyMatchPoints.push_back(flyKeypoints[matches[i].queryIdx].pt);
imgMatchPoints.push_back(imgKeypoints[matches[i].trainIdx].pt);
}

Mat H = findHomography(flyMatchPoints, imgMatchPoints, CV_RANSAC);

// Draw image for debug purposes
{
std::unique_lock<std::mutex> lck(debugMutex);
//drawKeypoints(grayFrame, imgKeypoints, g_imDebug);

drawMatches(flyTemplate, flyKeypoints, grayFrame, imgKeypoints,
matches, g_imDebug, Scalar::all(-1), Scalar::all(-1),
std::vector<char>(), DrawMatchesFlags::NOT_DRAW_SINGLE_POINTS);
}

FlyPose toReturn;
return toReturn;
}
*/