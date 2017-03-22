#ifndef ARDUINO_H
#define ARDUINO_H

using namespace System;
using namespace System::IO::Ports;

#define GRBL_MAX_VEL 10000
#define GRBL_MAX_ACC 200

#define GRBL_COM_PORT "COM4"
#define GRBL_BAUD_RATE 400000

// Struct for storing the move command to GRBL
struct GrblCommand{
	double x;
	double y;
};

// Struct for storing the results of a GRBL status query
public value struct GrblStatus
{
	bool isMoving;

	// Positions in millimeters
	double x;
	double y;
	double z;
};

// Global variable containing the CNC move command
GrblCommand g_moveCommand = { 0, 0 };

// Global variable containing the most recent GRBL status
GrblStatus g_grblStatus;

// Global variable used to signal when serial port should close
bool g_killSerial = false;

// Mutex to manage access to move command and CNC status
HANDLE g_moveMutex, g_statusMutex;

// Handle used to run SerialThread
HANDLE g_serialThread;

// High-level thread management
void StartSerialThread();
void StopSerialThread();

// Thread used to manage serial operations
DWORD WINAPI SerialThread(LPVOID lpParam);

public ref class GrblBoard
{
public:
	SerialPort^ arduino;
	GrblBoard();
	void Init();
	void Reset();
	void Close();
	void GrblCommand(int key, int value);
	void RawCommand(String^ cmdString);
	void StepIdleDelay(int value){ GrblCommand(1, value); }
	void StatusReportMask(int value){ GrblCommand(10, value); }
	void StepsPerMM_X(int value){ GrblCommand(100, value); }
	void StepsPerMM_Y(int value){ GrblCommand(101, value); }
	void MaxVelocityX(int value){ GrblCommand(110, value); }
	void MaxVelocityY(int value){ GrblCommand(111, value); }
	void MaxAccelerationX(int value){ GrblCommand(120, value); }
	void MaxAccelerationY(int value){ GrblCommand(121, value); }
	void SetUnitMM(){ RawCommand("G21"); }
	void MoveRelative(){ RawCommand("G91"); }
	void MaxFeedRate(int value);
	void Move(double X, double Y);
	void North() { Move(-1, 0); }
	void South() { Move(1, 0); }
	void East() { Move(0, 1); }
	void West() { Move(0, -1); }
	void ReadStatus();
};

#endif
