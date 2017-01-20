#ifndef ARDUINO_H
#define ARDUINO_H

using namespace System;
using namespace System::IO::Ports;

#define GRBL_MAX_VEL 10000
#define GRBL_MAX_ACC 200

// Stuff for storing grbl status upon query command ("?")
public value struct GrblStatus
{
	bool isMoving;

	// Positions in working units
	double x;
	double y;
	double z;
};

public ref class GrblBoard
{
public:
	SerialPort^ arduino;
	GrblBoard(SerialPort^ arduino);
	void Init();
	void Reset();
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
	GrblStatus ReadStatus();
};

#endif
