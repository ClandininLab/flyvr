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

#define DURATION 15.0
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

		// Compute the actual fly pose
		// TODO: fill in calculations
		Pose3D realPose;
		realPose.x = 0.0;
		realPose.y = 0.0;
		realPose.z = 0.0;
		realPose.roll = 0.0;
		realPose.pitch = 0.0;
		realPose.yaw = 0.0;

		// Compute the virtual fly pose
		// TODO: fill in calculations
		Pose3D virtualPose;
		virtualPose.x = 0.0;
		virtualPose.y = 0.0;
		virtualPose.z = 0.0;
		virtualPose.roll = 0.0;
		virtualPose.pitch = 0.0;
		virtualPose.yaw = 0.0;

		// Send pose command
		LOCK(g_ogreMutex);
			g_virtualPose = virtualPose;
			g_realPose = realPose;
		UNLOCK(g_ogreMutex);

		deltaT = (GetTimeStamp() - startTime) * TIMER_SCALE_FACTOR;
	}
	
	//StopCameraThread();
	//StopSerialThread();
	StopGraphicsThread();

	return 0;
}