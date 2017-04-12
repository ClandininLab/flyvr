// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef ARDUINO_H
#define ARDUINO_H

#include <mutex>
#include <thread>
#include <memory>

#include "Serial.h"

enum class GrblAxis {X, Y};

// Mutex to manage access to move command and CNC status
extern std::mutex g_moveMutex, g_statusMutex;

// Struct for storing the move command to GRBL
struct GrblCommand{
	double x;
	double y;
};

// GRBL states
enum class GrblStates {Idle, Run, Home, Alarm};

// Global variable containing the CNC move command
extern GrblCommand g_moveCommand;

// Struct for storing the results of a GRBL status query
struct GrblStatus
{
	GrblStates state;

	// Positions in millimeters
	double x;
	double y;
	double z;
};

// Global variable containing the most recent GRBL status
extern GrblStatus g_grblStatus;

// High-level thread management
void StartSerialThread();
void StopSerialThread();

// Thread used to manage serial operations
void SerialThread(void);

class GrblBoard
{
public:
	// Constructor, requires that the serial port has already been opened
	GrblBoard();

	// Reads out the GRBL status (position and moving/idle condition)
	void ReadStatus();

	// General move command
	void Move(double X, double Y);

	// Home to origin
	void Home();

	// Waits until rig stops moving
	void WaitToStop();

	// Resets the GRBL board
	void Reset();

private:
	// Serial port used for communication with GRBL board
	std::unique_ptr<Serial> arduino{};

	// Read from configuration file
	void ReadSerialConfig(const char* loc);

	// Read the status string from GRBL
	std::string GrblBoard::GetStatusString();

	// Low-level communication routines
	void GrblCommand(int key, int value);
	void RawCommand(std::string cmdString);

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
	void SetupStatusReport(void){ GrblCommand(10, 1); }
	void SetUnitMM(){ RawCommand("G21"); }
	void MoveRelative(){ RawCommand("G91"); }

	// Configuration variables
	double JogAmount;
	unsigned MaxVel;
	unsigned MaxAcc;
	unsigned StepsPerMM_X;
	unsigned StepsPerMM_Y;
	int HomingPullOff, HomingDebounce, HomingFeedRate, HomingSeekRate;

	// COM port configuration
	std::string ComPort;
	unsigned BaudRate;
};

#endif