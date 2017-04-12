// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <iostream>
#include <future>
#include <SimpleIni.h>

#define _USE_MATH_DEFINES
#include <math.h>

#include <conio.h>

#include "Tracker.h"
#include "OgreApplication.h"
#include "Camera.h"
#include "Arduino.h"

using namespace std::chrono;

// Actions for key presses
enum class KeyPressAction { Quit, Up, Down, Left, Right, None };

// Name of configuration file for tracker
auto TrackerConfigFile = "tracker.ini";

// Configuration parameters to be read from INI file
double MaxDuration; // seconds
double TargetLoopDuration; // seconds
double MinMove; // millimeters
double MaxMove; // millimeters
double JogAmount; // millimeters

void ReadTrackerConfig(){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(TrackerConfigFile);

	// Read in values from INI file
	MaxDuration = iniFile.GetDoubleValue("", "max-duration", 25);
	TargetLoopDuration = iniFile.GetDoubleValue("", "target-loop-duration", 10e-3);
	MinMove = iniFile.GetDoubleValue("", "min-move", 1);
	MaxMove = iniFile.GetDoubleValue("", "max-move", 40);
	JogAmount = iniFile.GetDoubleValue("", "jog-amount", 1);
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

KeyPressAction GetKeyPress(){
	if (_kbhit()){
		int key = _getch();
		if (key == 0 || key == 224){
			key = _getch();
			if (key == 72){
				return KeyPressAction::Up;
			}
			else if (key == 80){
				return KeyPressAction::Down;
			}
			else if (key == 75){
				return KeyPressAction::Left;
			}
			else if (key == 77){
				return KeyPressAction::Right;
			}
		}
		else if (key == 27){
			return KeyPressAction::Quit;
		}
	}

	// Otherwise just return no action
	return KeyPressAction::None;
}

void SendMoveCommand(double x, double y){
	// Send move command
	{
		std::unique_lock<std::mutex> lck{ g_moveMutex };
		g_moveCommand = { x, y };
	}
}

int main() {
	ReadTrackerConfig();

	StartGraphicsThread();
	StartSerialThread();
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

		// Handle key presses
		auto action = GetKeyPress();
		if (action == KeyPressAction::Up){
			SendMoveCommand(-JogAmount, 0);
		}
		else if (action == KeyPressAction::Down){
			SendMoveCommand(JogAmount, 0);
		}
		else if (action == KeyPressAction::Left){
			SendMoveCommand(0, -JogAmount);
		}
		else if (action == KeyPressAction::Right){
			SendMoveCommand(0, JogAmount);
		}
		else if (action == KeyPressAction::Quit){
			break;
		}
		
	} while (trackerDuration < MaxDuration);

	//StopCameraThread();
	StopSerialThread();
	StopGraphicsThread();

	return 0;
}
