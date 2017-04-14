// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <iostream>
#include <future>
#include <numeric>
#include <SimpleIni.h>

#define _USE_MATH_DEFINES
#include <math.h>

#include <conio.h>

#include "Tracker.h"
#include "OgreApplication.h"
#include "Camera.h"
#include "Arduino.h"
#include "Utility.h"

using namespace std::chrono;

// Actions for key presses
enum class KeyPressAction { Quit, Up, Down, Left, Right, Status, None };

// Name of configuration file for tracker
auto TrackerConfigFile = "tracker.ini";

// Configuration parameters to be read from INI file
double MaxDuration; // seconds
double TargetLoopDuration; // seconds
double MinMove; // millimeters
double MaxMove; // millimeters
double JogAmount; // millimeters
double CenterX; // millimeters
double CenterY; // millimeters
double FlyY; // meters
long AngleFilterLength;
std::vector<double> angleList;

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

	// Center position
	CenterX = iniFile.GetDoubleValue("", "center-x", -315);
	CenterY = iniFile.GetDoubleValue("", "center-y", -351);
	FlyY = iniFile.GetDoubleValue("", "fly-y", -0.3113);

	AngleFilterLength = iniFile.GetLongValue("", "angle-filter-length", 10);
	angleList = std::vector<double>(AngleFilterLength, 0.0);
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
		else if (char(key) == 's'){
			return KeyPressAction::Status;
		}
		else if (key == 27){
			return KeyPressAction::Quit;
		}
	}

	// Otherwise just return no action
	return KeyPressAction::None;
}

double filterAngle(double angle){
	for (unsigned i = AngleFilterLength - 1; i >= 1; i--){
		angleList[i] = angleList[i - 1];
	}
	angleList[0] = angle;

	double average = std::accumulate(angleList.begin(), angleList.end(), 0.0) / angleList.size();

	return average;
 }

int main() {
	ReadTrackerConfig();

	StartSerialThread();

	std::cout << "Moving to start location\n";
	GrblMoveCommand(CenterX, CenterY);
	WaitForIdle();
	std::cout << "Done\n";

	StartGraphicsThread();
	StartCameraThread();
	
	auto trackerStart = high_resolution_clock::now();
	double trackerDuration;

	do {
		auto loopStart = high_resolution_clock::now();

		// Get fly pose
		FlyPose fly = GetFlyPose();

		// Get CNC position
		GrblStatus grbl = GetGrblStatus();

		// Update graphics with fly position, if a fly is present
		if (fly.present){
			Pose3D flyPose;
			flyPose.x = (grbl.y + fly.y - CenterY) * 1e-3;  // + X graphics is +Y GRBL, +Y Camera
			flyPose.y = FlyY;
			flyPose.z = (grbl.x - fly.x - CenterX) * 1e-3; // + Z graphics is +X GRBL, -X Camera
			flyPose.pitch = 0;
			flyPose.yaw = filterAngle(-fly.angle) * M_PI/180.0; // TODO: check the sign
			flyPose.roll = 0;

			SetFlyPose3D(flyPose);
		}

		// Handle key presses
		auto action = GetKeyPress();
		if (action == KeyPressAction::Up){
			GrblMoveCommand(grbl.x - JogAmount, grbl.y);
		}
		else if (action == KeyPressAction::Down){
			GrblMoveCommand(grbl.x + JogAmount, grbl.y);
		}
		else if (action == KeyPressAction::Left){
			GrblMoveCommand(grbl.x, grbl.y - JogAmount);
		}
		else if (action == KeyPressAction::Right){
			GrblMoveCommand(grbl.x, grbl.y + JogAmount);
		}
		else if (action == KeyPressAction::Status){
			std::cout << "GRBL: <" << grbl.x << ", " << grbl.y << ">\n";
			if (fly.present){
				std::cout << "Fly: <" << fly.x << ", " << fly.y << ">\n";
			}
		}
		else if (action == KeyPressAction::Quit){
			break;
		}
		else {
			if (fly.present){
				double dx = clamp(-fly.x, MinMove, MaxMove);
				double dy = clamp(fly.y, MinMove, MaxMove);
				GrblMoveCommand(grbl.x + dx, grbl.y + dy);
			}
		}

		// Aim for a target loop rate
		auto loopStop = high_resolution_clock::now();
		auto loopDuration = duration<double>(loopStop - loopStart).count();
		if (loopDuration < TargetLoopDuration){
			DelaySeconds(TargetLoopDuration - loopDuration);
		}

		// Compute cumulative duration
		trackerDuration = duration<double>(loopStop - trackerStart).count();

	} while (trackerDuration < MaxDuration);

	StopCameraThread();
	StopGraphicsThread();
	StopSerialThread();

	return 0;
}
