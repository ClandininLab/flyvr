#include "stdafx.h"

#include <windows.h>
#include "Camera.h"
#include "timer.h"
#include "mutex.h"

using namespace System;
using namespace System::IO;

// High-level management of the graphics thread
void StartCameraThread(){
	// Graphics setup
	g_cameraMutex = CreateMutex(NULL, FALSE, NULL);
	DWORD cameraThreadID;
	g_cameraThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)CameraThread, NULL, 0, &cameraThreadID);
}

void StopCameraThread(){
	// Kill the 3D graphics thread
	g_killCamera = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(g_cameraThread, INFINITE);

	// Close the handles to the mutexes and graphics thread
	CloseHandle(g_cameraThread);
	CloseHandle(g_cameraMutex);
}

// Thread used to handle graphics operations
DWORD WINAPI CameraThread(LPVOID lpParam){
	// Set up logging
	StreamWriter^ logger = gcnew StreamWriter("CameraThread.txt");
	logger->WriteLine("x (mm),y (mm),angle (deg),timestamp (100ns)");

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, CV_FRAME_WIDTH);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, CV_FRAME_HEIGHT);

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
			__int64 tstamp = GetTimeStamp();

			// Format the data output
			System::String^ data = System::String::Format(
				"{0:0.000},{1:0.000},{2:0.000},{3}",
				g_camPose.x,
				g_camPose.y,
				g_camPose.angle,
				tstamp);

			logger->WriteLine(data);
		}
	}

	// Close the log file
	logger->Close();

	return TRUE;
}

void prepFrame(){
	// Convert to grayscale
	cvtColor(g_origFrame, g_procFrame, CV_BGR2GRAY);

	// Blur the image to reduce noise
	blur(g_procFrame, g_procFrame, Size(CV_BLUR_SIZE, CV_BLUR_SIZE));

	// Crop the image to remove edge effects of blurring
	g_procFrame = g_procFrame(Rect(CV_CROP_AMOUNT, CV_CROP_AMOUNT, CV_CROPPED_WIDTH, CV_CROPPED_HEIGHT));

	// Threshold image to produce black-and-white result
	threshold(g_procFrame, g_procFrame, CV_LOW_THRESH, CV_HIGH_THRESH, THRESH_BINARY_INV);
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
	if (sizeMax > CV_MIN_CONTOUR){
		g_boundingBox = fitEllipse(Mat(*maxElem));

		// Compute fly position
		double x = (g_boundingBox.center.x - CV_CROPPED_WIDTH / 2.0) / CV_PIXEL_PER_MM;
		double y = (g_boundingBox.center.y - CV_CROPPED_HEIGHT / 2.0) / CV_PIXEL_PER_MM;
		double angle = g_boundingBox.angle;

		// Update shared position
		LOCK(g_cameraMutex);
			g_camPose.x = x;
			g_camPose.y = y;
			g_camPose.angle = angle;
		UNLOCK(g_cameraMutex);

		return true;
	}
	else {
		return false;
	}
}