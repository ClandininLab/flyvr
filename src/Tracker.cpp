// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <iostream>
#include <future>
#include <numeric>
#include <direct.h>  
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

namespace TrackerNamespace{
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
	double UnwrapThresh; // degrees
	std::vector<double> angleList;

	bool EnableGraphicsThread;
	bool EnableSerialThread;
	bool EnableCameraThread;
}

using namespace TrackerNamespace;

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
	UnwrapThresh = iniFile.GetDoubleValue("", "unwrap-threshold", 150.0);
	angleList = std::vector<double>(AngleFilterLength, 0.0);

	// Thread variables
	EnableGraphicsThread = iniFile.GetBoolValue("", "enable-graphics-thread", true);
	EnableSerialThread = iniFile.GetBoolValue("", "enable-serial-thread", true);
	EnableCameraThread = iniFile.GetBoolValue("", "enable-camera-thread", true);
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

double unwrapAngle(double val, double old){
	while (val - old > UnwrapThresh){
		val -= 180.0;
	}
	while (old - val > UnwrapThresh){
		val += 180.0;
	}
	return val;
}

int main(int argc, char* argv[]) {
	std::string stimFile;
	std::string outDir;

	if (argc == 1){
		stimFile = "config.ini";
		outDir = "out";
	}
	else if (argc == 3){
		stimFile = argv[1];
		outDir = argv[2];
	}
	else {
		throw std::runtime_error("Invalid number of arguments.");
	}

	// Make the output directory if necessary
	_mkdir(outDir.c_str());

	ReadTrackerConfig();

	if (EnableSerialThread){
		StartSerialThread(outDir);
		std::cout << "Moving to start location\n";
		GrblMoveCommand(CenterX, CenterY);
		WaitForIdle();
		std::cout << "Done\n";
	}

	if (EnableGraphicsThread){
		StartGraphicsThread(stimFile, outDir);
	}

	if (EnableCameraThread){
		StartCameraThread(outDir);
	}
	
	// Create timing manager for the loop
	TimeManager timeManager("MainThread");
	timeManager.start();

	FlyPose fly, lastFly;
	GrblStatus grbl;

	do {
		// Log start of loop
		timeManager.tick();

		// Get the new fly pose
		if (EnableCameraThread){
			fly = GetFlyPose();
		}
		bool flyPresent = fly.present && fly.valid;
		bool lastFlyPresent = lastFly.present && lastFly.valid;

		// Get CNC position
		if (EnableSerialThread){
			grbl = GetGrblStatus();
		}

		// Update graphics with fly position, if a fly is present
		if (flyPresent && lastFlyPresent && grbl.valid){
			fly.angle = unwrapAngle(fly.angle, lastFly.angle);

			Pose3D flyPose;
			flyPose.x = (grbl.y + fly.y - CenterY) * 1e-3;  // + X graphics is +Y GRBL, +Y Camera
			flyPose.y = FlyY;
			flyPose.z = (grbl.x - fly.x - CenterX) * 1e-3; // + Z graphics is +X GRBL, -X Camera
			flyPose.pitch = 0;
			flyPose.yaw = filterAngle(-fly.angle) * M_PI / 180.0; // TODO: check the sign
			flyPose.roll = 0;

			if (EnableGraphicsThread){
				SetFlyPose3D(flyPose);
			}
		}

		// Handle key presses
		auto action = GetKeyPress();
		if (action == KeyPressAction::Up){
			if (grbl.valid){
				GrblMoveCommand(grbl.x - JogAmount, grbl.y);
			}
		}
		else if (action == KeyPressAction::Down){
			if (grbl.valid){
				GrblMoveCommand(grbl.x + JogAmount, grbl.y);
			}
		}
		else if (action == KeyPressAction::Left){
			if (grbl.valid){
				GrblMoveCommand(grbl.x, grbl.y - JogAmount);
			}
		}
		else if (action == KeyPressAction::Right){
			if (grbl.valid){
				GrblMoveCommand(grbl.x, grbl.y + JogAmount);
			}
		}
		else if (action == KeyPressAction::Status){
			if (grbl.valid){
				std::cout << "GRBL: <" << grbl.x << ", " << grbl.y << ">\n";
			}
			if (flyPresent){
				std::cout << "Fly: <" << fly.x << ", " << fly.y << ">\n";
			}
		}
		else if (action == KeyPressAction::Quit){
			break;
		}
		else {
			if (flyPresent && grbl.valid){
				double dx = clamp(-fly.x, MinMove, MaxMove);
				double dy = clamp(fly.y, MinMove, MaxMove);
				GrblMoveCommand(grbl.x + dx, grbl.y + dy);
			}
		}

		// Save fly pose if there was a fly present
		if (flyPresent){
			lastFly = fly;
		}

		// Wait if necessary to ensure a maximum loop rate
		timeManager.waitUntil(TargetLoopDuration);

	} while (timeManager.totalDuration() < MaxDuration);

	if (EnableCameraThread){
		StopCameraThread();
	}
	if (EnableGraphicsThread){
		StopGraphicsThread();
	}
	if (EnableSerialThread){
		StopSerialThread();
	}

	return 0;
}
