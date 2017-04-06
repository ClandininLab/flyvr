// Tracker.cpp : main project file.

#include "stdafx.h"

#define _USE_MATH_DEFINES
#include <math.h>

#include <windows.h>

#include "OgreApplication.h"
#include "Camera.h"
#include "arduino.h"
#include "timer.h"
#include "mutex.h"

#pragma comment(lib, "user32.lib")

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;

#define DURATION 60
#define MIN_MOVE 1
#define MAX_MOVE 40

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
	
	__int64 startTime = GetTimeStamp();
	double deltaT = 0.0;

	while (deltaT < DURATION){
		
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

		deltaT = (GetTimeStamp() - startTime) * TIMER_SCALE_FACTOR;

		LOCK(g_ogreMutex);
		//g_realPose.yaw = M_PI/2 - M_PI*(deltaT / DURATION);
		//g_realPose.z = -(DISPLAY_WIDTH_METERS/2)*(deltaT / DURATION);
		
		g_virtPose = g_realPose; // simulate real motion
		UNLOCK(g_ogreMutex);
	}
	
	//StopCameraThread();
	//StopSerialThread();
	StopGraphicsThread();

	return 0;
}