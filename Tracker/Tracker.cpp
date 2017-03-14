// Tracker.cpp : main project file.

#include "stdafx.h"

#include "OgreApplication.h"

#include <windows.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

#include "arduino.h"
#include "timer.h"

#define _USE_MATH_DEFINES
#include <math.h>

#pragma comment(lib, "user32.lib")

#define N_FILT 100

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;
using namespace cv;

// Global variables containing the move command
double xMove = 0.0;
double yMove = 0.0;

// Global variables containing the last known GRBL position
double xStatus = 0.0;
double yStatus = 0.0;

// Global variable used to signal when serial port should close
bool killSerial = false;

// Global variable used to signal when the Ogre3D window should close
bool kill3D = false;

// Global variable used to indicate when the Ogre3D engine is running
bool readyFor3D = false;

// Mutex to manage access to xMove and yMove
HANDLE coordMutex;

// Mutex to manage access to 3D graphics variables
HANDLE gfxMutex;

DWORD WINAPI SerialThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);

	// Create the timer
	DebugTimer^ loopTimer = gcnew DebugTimer("serial_loop_time.txt");

	GrblBoard ^grbl;
	GrblStatus status;

	double xMoveLocal = 0.0;
	double yMoveLocal = 0.0;

	// Connect to GRBL
	grbl = gcnew GrblBoard();

	// Continually poll GRBL status and move if desired
	while (!killSerial){
		loopTimer->Tick();

		// Read the current status
		status = grbl->ReadStatus();

		// Lock access to global coordinates
		WaitForSingleObject(coordMutex, INFINITE);

		// Read out the move command and reset it to zero
		xMoveLocal = xMove;
		yMoveLocal = yMove;
		xMove = 0.0;
		yMove = 0.0;

		// Update the GRBL position
		xStatus = status.x;
		yStatus = status.y;

		// Release access to xMove and yMove
		ReleaseMutex(coordMutex);

		// Run the move command if applicable
		if ((xMoveLocal != 0.0 || yMoveLocal != 0.0) && !status.isMoving){
			grbl->Move(xMoveLocal, yMoveLocal);
		}

		loopTimer->Tock();
	}

	// Close streams
	loopTimer->Close();
	grbl->Close();

	return TRUE;
}

// clamp "value" between "min" and "max"
double clamp(double value, double min, double max){
	if (abs(value) < min){
		return 0.0;
	}
	else if (value < -max){
		return -max;
	}
	else if (value > max) {
		return max;
	}
	else {
		return value;
	}
}

struct Triple{
	double x;
	double y;
	double z;
};
Triple cameras[DISPLAY_COUNT];
Triple looks[DISPLAY_COUNT];

double pattern_rotation = 0.0;

DWORD WINAPI GraphicsThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);
	OgreApplication app;
	Triple cameras_local[DISPLAY_COUNT];
	Triple looks_local[DISPLAY_COUNT];
	double pattern_rotation_local;
	try {
		app.go();
		readyFor3D = true;
		while (!kill3D){
			// Copy over the camera position information
			WaitForSingleObject(gfxMutex, INFINITE);
			memcpy(&cameras_local, &cameras, sizeof(cameras));
			memcpy(&looks_local, &looks, sizeof(looks));
			pattern_rotation_local = pattern_rotation;
			ReleaseMutex(gfxMutex);

			// Reposition the cameras
			for (unsigned i = 0; i < DISPLAY_COUNT; i++){
				app.setCameraPosition(cameras_local[i].x, cameras_local[i].y, cameras_local[i].z, i);
				app.setCameraTarget(looks_local[i].x, looks_local[i].y, looks_local[i].z, i);
			}

			// Rotate pattern
			app.setPatternRotation(pattern_rotation_local);

			// Render the frame
			app.renderOneFrame();
		}
	}
	catch (Ogre::Exception& e) {
		std::cerr << "An exception has occured: " <<
			e.getFullDescription().c_str() << std::endl;
	}
	return TRUE;
}

int main() {
	// Create the timer
	DebugTimer^ loopTimer = gcnew DebugTimer("main_loop_time.txt");

	// GRBL Setup
	HANDLE serialThread;
	DWORD serThreadID;
	serialThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)SerialThread, NULL, 0, &serThreadID);
	coordMutex = CreateMutex(NULL, FALSE, NULL);

	double minMove = 1;
	double maxMove = 40;

	double angleDelta = 2*M_PI/3000;

	// Initialize camera configurations
	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
		// Camera positions
		cameras[i].x = 0;
		cameras[i].y = 0;
		cameras[i].z = 0;

		// Camera targets
		looks[i].x = cameras[i].x;
		looks[i].y = cameras[i].y;
		looks[i].z = cameras[i].z;
	}

	looks[NORTH].z = cameras[NORTH].z-1;
	looks[WEST].x = cameras[WEST].x-1;
	looks[EAST].x = cameras[WEST].x+1;

	// Graphics setup
	gfxMutex = CreateMutex(NULL, FALSE, NULL);
	HANDLE graphicsThread;
	DWORD gfxThreadID;
	graphicsThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)GraphicsThread, NULL, 0, &gfxThreadID);

	// Wait for 3D engine to be up and running
	while (!readyFor3D);
	
	// Camera setup
	int width = 200;
	int height = 200;
	int blur_size = 10;
	int buffer = blur_size;
	int cropped_width = width - 2 * buffer;
	int cropped_height = height - 2 * buffer;

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, width);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, height);

	// Original, unprocessed, captured frame from the camera.
	Mat im, src;
	RotatedRect box;
	vector<vector<Point>> contours;
	vector<Vec4i> hierarchy;

	double xCam, yCam, xMoveLocal, yMoveLocal, aCam;
	double xStatusLocal, yStatusLocal;

	double filt_array[N_FILT];
	double lastAngle = 0.0;
	double unwrapTol = 160.0;
	for (unsigned i = 0; i < N_FILT; i++){
		filt_array[i] = 0.0;
	}

	for (int i = 0; i < 3000; i++){

		// Update graphics display
		WaitForSingleObject(gfxMutex, INFINITE);
		pattern_rotation += angleDelta;
		ReleaseMutex(gfxMutex);

		loopTimer->Tick();

		// Read image
		cap.read(src);

		// Crop, convert to grayscale, threshold
		cvtColor(src, im, CV_BGR2GRAY);
		blur(im, im, Size(blur_size, blur_size));
		im = im(Rect(buffer, buffer, cropped_width, cropped_height));
		threshold(im, im, 110, 255, THRESH_BINARY_INV);

		// Detect contours
		findContours(im, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

		// Find biggest contour
		int idx_max = -1;
		size_t size_max = 0;
		for (int idx = 0; idx < contours.size(); idx++){
			if (contours[idx].size() > size_max){
				size_max = contours[idx].size();
				idx_max = idx;
			}
		}

		// Fit ellipse
		if (size_max > 5){
			box = fitEllipse(Mat(contours[idx_max]));
			src = src(Rect(buffer, buffer, cropped_width, cropped_height));
			ellipse(src, box, Scalar(0,0,255), 2, 8);
			//imshow("Result", src);
			//waitKey(1);
		} else {
			loopTimer->Tock("0.000,0.000,0.000,0.000,0.000,{0:0.000}");
			src = src(Rect(buffer, buffer, cropped_width, cropped_height));
			//imshow("Result", src);
			//waitKey(1);
			continue;
		}

		// Calculate coordinates of the dot with respect to the center of the frame
		xCam = box.center.x - cropped_width/2.0;
		yCam = box.center.y - cropped_height/2.0;
		aCam = box.angle;

		// Unwrap angle
		while (lastAngle - aCam > unwrapTol){
			aCam += 180.0;
		}
		while (aCam - lastAngle > unwrapTol){
			aCam -= 180.0;
		}

		// Scale coordinates to mm
		xCam = xCam / 9.1051;
		yCam = yCam / 9.1051;

		// Calculate move command
		xMoveLocal = clamp(-xCam, minMove, maxMove);
		yMoveLocal = clamp(yCam, minMove, maxMove);

		// Lock access to coordinate data
		WaitForSingleObject(coordMutex, INFINITE);

		xMove = xMoveLocal;
		yMove = yMoveLocal;

		xStatusLocal = xStatus;
		yStatusLocal = yStatus;

		// Release access to coordinate data
		ReleaseMutex(coordMutex);

		// Update filter buffer
		for (unsigned i = N_FILT-1; i >= 1; i--){
			filt_array[i] = filt_array[i - 1];
		}
		filt_array[0] = aCam;

		// Update filtered angle
		double aCam_filt = 0.0;
		for (unsigned i = 0; i < N_FILT; i++){
			aCam_filt += filt_array[i];
		}
		aCam_filt /= 1.0*N_FILT;

		// Format data for logging
		System::String^ format = System::String::Format("{0:0.000},{1:0.000},{2:0.000},{3:0.000},{4:0.000},{{0:0.000}}", 
			xCam, yCam, xStatusLocal, yStatusLocal, aCam);

		// Log data
		loopTimer->Tock(format);
	}
	
	// Close streams
	loopTimer->Close();

	// Kill the serial thread
	killSerial = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(serialThread, INFINITE);

	// Close the handles to the mutexes and serial thread
	CloseHandle(serialThread);
	CloseHandle(coordMutex);

	// Kill the 3D graphics thread
	kill3D = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(graphicsThread, INFINITE);

	// Close the handles to the mutexes and graphics thread
	CloseHandle(graphicsThread);
	CloseHandle(gfxMutex);

	return 0;
}