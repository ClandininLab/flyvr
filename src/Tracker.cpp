// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <SimpleIni.h>

#define _USE_MATH_DEFINES
#include <math.h>

#include "Tracker.h"
#include "OgreApplication.h"
#include "Camera.h"
//#include "Arduino.h"

using namespace std::chrono;

// Name of configuration file for tracker
auto TrackerConfigFile = "tracker.ini";

// Configuration parameters to be read from INI file
double Duration = 25; // seconds
double TargetLoopDuration = 10e-3; // seconds
double MinMove = 1; // millimeters
double MaxMove = 40; // millimeters

void ReadTrackerConfig(){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(TrackerConfigFile);

	// Read in values from INI file
	Duration = iniFile.GetDoubleValue("", "duration", 25);
	TargetLoopDuration = iniFile.GetDoubleValue("", "target-loop-duration", 10e-3);
	MinMove = iniFile.GetDoubleValue("", "min-move", 1);
	MaxMove = iniFile.GetDoubleValue("", "duration", 40);
}

// Function to clamp a value between minimum and maximum bounds
double clamp(double value, double min, double max){
	if (std::abs(value) < min){
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
	ReadTrackerConfig();

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

		{
			std::unique_lock<std::mutex> lck{ g_ogreMutex };
			//g_realPose.yaw = M_PI/2 - M_PI*(deltaT / DURATION);
			//g_realPose.z = -(DISPLAY_WIDTH_METERS/2)*(deltaT / DURATION);

			g_virtPose = g_realPose; // simulate real motion
		}

		// Aim for a target loop rate

		auto loopStop = high_resolution_clock::now();
		auto loopDuration = duration<double>(loopStop - loopStart).count();
		if (loopDuration < TargetLoopDuration){
			auto stopTime = loopStart + duration<double>(TargetLoopDuration);
			std::this_thread::sleep_until(stopTime);
		}

		// Compute cumulative duration
		trackerDuration = duration<double>(loopStop - trackerStart).count();

	} while (trackerDuration < Duration);

	//StopCameraThread();
	//StopSerialThread();
	StopGraphicsThread();

	return 0;
}
