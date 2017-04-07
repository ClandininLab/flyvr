// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#define _USE_MATH_DEFINES
#include <math.h>
#include <chrono>

#include <windows.h>

#include "OgreApplication.h"
#include "Camera.h"
#include "arduino.h"
#include "mutex.h"

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;

using namespace std::chrono;

#define DURATION 60
#define MIN_MOVE 1
#define MAX_MOVE 40

#define TRACKER_LOOP_DURATION 10e-3

// Function to clamp a value between minimum and maximum bounds
double clamp(double value, double min, double max){
	if (abs(value) < min){
		return 0.0;
	}
	else if (value < -max) {
		return -max;
	}
	else if (value > max) {
		return max;
	}
	else {
		return value;
	}
}

int main() {
	StartGraphicsThread();
	//StartSerialThread();
	//StartCameraThread();
	
	auto trackerStart = high_resolution_clock::now();
	double trackerDuration;

	do {
		auto loopStart = high_resolution_clock::now();

		// Get fly pose
		//CamPose camPose;
		//LOCK(g_cameraMutex);
		//	camPose = g_camPose;
		//UNLOCK(g_cameraMutex);

		// Calculate move command
		//GrblCommand moveCommand;
		//moveCommand.x = clamp(-camPose.x, MIN_MOVE, MAX_MOVE);
		//moveCommand.y = clamp(camPose.y, MIN_MOVE, MAX_MOVE);

		// Send move command
		//LOCK(g_moveMutex);
		//	g_moveCommand = moveCommand;
		//UNLOCK(g_moveMutex);

		// Get CNC position
		//GrblStatus grblStatus;
		//LOCK(g_statusMutex);
		//	grblStatus = g_grblStatus;
		//UNLOCK(g_statusMutex);

		LOCK(g_ogreMutex);
		//g_realPose.yaw = M_PI/2 - M_PI*(deltaT / DURATION);
		//g_realPose.z = -(DISPLAY_WIDTH_METERS/2)*(deltaT / DURATION);
		
		g_virtPose = g_realPose; // simulate real motion
		UNLOCK(g_ogreMutex);

		// Aim for a target loop rate
		auto loopStop = high_resolution_clock::now();
		auto loopDuration = duration<double>(loopStop - loopStart).count();
		if (loopDuration < TRACKER_LOOP_DURATION){
			Sleep(round(1000 * (TRACKER_LOOP_DURATION - loopDuration)));
		}

		// Compute cumulative duration
		trackerDuration = duration<double>(loopStop - trackerStart).count();
	} while (trackerDuration < DURATION);
	
	//StopCameraThread();
	//StopSerialThread();
	StopGraphicsThread();

	return 0;
}