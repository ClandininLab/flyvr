// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef ARDUINO_H
#define ARDUINO_H

#include <thread>
#include <memory>
#include <regex>

#include "Serial.h"

enum class GrblAxis {X, Y};

// Struct for storing the move command to GRBL
struct GrblCommand{
	double x;
	double y;
	bool fresh;
	GrblCommand() : x(0), y(0), fresh(false) {}
};

// GRBL states
enum class GrblStates {Idle, Run, Home, Alarm, Jog};

// Struct for storing the results of a GRBL status query
struct GrblStatus
{
	GrblStates state;

	// Positions in millimeters
	double x;
	double y;
	double z;

	// Buffer availability
	unsigned planBuf;
	unsigned rxBuf;

	double tstamp;

	// Validity indicator, false initially
	bool valid;

	GrblStatus() : x(0), y(0), z(0), tstamp(0), valid(false) {}
};

// High-level thread management
void StartSerialThread(std::string outDir);
void StopSerialThread();

// Interface functions for other threads
void GrblMoveCommand(double x, double y);
GrblStatus GetGrblStatus(void);
void WaitForIdle(void);

// Thread used to manage serial operations
void SerialThread(void);

class GrblBoard
{
public:
	// Constructor, requires that the serial port has already been opened
	GrblBoard();

	// Reads out the GRBL status (position and moving/idle condition)
	GrblStatus ReadStatus();

	// General move command
	void Move(double X, double Y);

	// Home to origin
	void Home();

	// Waits until rig stops moving
	void WaitToStop();

	// Resets the GRBL board
	void Reset();

	double TargetLoopDuration;

private:
	// Serial port used for communication with GRBL board
	std::unique_ptr<Serial> arduino{};

	// Read from configuration file
	void ReadSerialConfig(const char* loc);

	// Low-level communication routines
	void GrblCommand(int key, int value);
	std::string RawCommand(std::string cmdString, bool newLine=true);

	// Commands used in the initialization of GRBL
	void Init();
	void Config();
	void StepsPerMM(int value, GrblAxis axis);
	void MaxVelocity(int value, GrblAxis axis);
	void MaxAcceleration(int value, GrblAxis axis);
	void MaxFeedRate(int value);

	// One-liner commandss
	void EnableHardLimits(void){ GrblCommand(21, 1); }
	void EnableHoming(void){ GrblCommand(22, 1); }
	void SetHomingPullOff(int mm){ GrblCommand(27, mm);  }
	void SetHomingDebounce(int ms){ GrblCommand(26, ms); }
	void SetHomingFeedRate(int mm_per_min){ GrblCommand(24, mm_per_min); }
	void SetHomingSeekRate(int mm_per_min){ GrblCommand(25, mm_per_min); }
	void BrakeAfterMovement(void){ GrblCommand(1, 255); }
	void SetupStatusReport(void){ GrblCommand(10, 2); }
	void SetUnitMM(){ RawCommand("G21"); }
	void MoveAbsolute(){ RawCommand("G90"); }

	// Configuration variables
	double MaxTravelX, MaxTravelY;
	unsigned MaxVel;
	unsigned MaxAcc;
	unsigned StepsPerMM_X;
	unsigned StepsPerMM_Y;
	int HomingPullOff, HomingDebounce, HomingFeedRate, HomingSeekRate;

	// Amount of time to wait before sending serial to arduino
	double ArduinoDelay;

	// COM port configuration
	std::string ComPort;
	unsigned BaudRate;
};

#endif