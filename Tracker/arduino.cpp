#include "stdafx.h"
#include <windows.h>

using namespace System;
using namespace System::IO::Ports;
using namespace System::Text::RegularExpressions;

#include "arduino.h"

// Method definition for GrblBoard class
GrblBoard::GrblBoard(SerialPort^ arduino){
	this->arduino = arduino;
}
void GrblBoard::Init(){
	StepIdleDelay(255); // causes stepper motor to hold position after movement
	StatusReportMask(1); // status will include running state and machine position
	StepsPerMM_X(40); // number of steps per millimeter of X movement
	StepsPerMM_Y(40); // number of steps per millimeter of Y movement
	MaxVelocityX(GRBL_MAX_VEL); // maximum X velocity, in mm/min
	MaxVelocityY(GRBL_MAX_VEL); // maximum Y velocity, in mm/min
	MaxAccelerationX(GRBL_MAX_ACC); // maximum X acceleration, in mm/sec^2
	MaxAccelerationY(GRBL_MAX_ACC); // maximum Y acceleration, in mm/sec^2
	SetUnitMM(); // all measurements in millimeters
	MaxFeedRate(GRBL_MAX_VEL); // maximum feed rate, in mm/min
	MoveRelative(); // use relative movement, rather than absolute
}
void GrblBoard::Reset(){
	arduino->WriteLine("\x18");
}
void GrblBoard::GrblCommand(int key, int value){
	String^ cmdString = String::Format("${0}={1}", key, value);
	arduino->WriteLine(cmdString);
}
void GrblBoard::RawCommand(String^ cmdString){
	arduino->WriteLine(cmdString);
}
void GrblBoard::MaxFeedRate(int value){
	String^ cmdString = String::Format("F{0}", value);
	RawCommand(cmdString);
}
void GrblBoard::Move(double X, double Y){
	String^ cmdString = String::Format("G1X{0:0.000}Y{1:0.000}", X, Y);
	arduino->WriteLine(cmdString);
}
GrblStatus GrblBoard::ReadStatus(){
	arduino->DiscardInBuffer();
	arduino->WriteLine("?");
	
	// Read response from GRBL
	// example:
	// <Idle, MPos:-100.000,-100.000,0.000>
	String^ resp = arduino->ReadLine();

	// Match 
	Regex^ regex = gcnew Regex("<\\s*(Idle|Run),\\s*MPos:\\s*(-?\\d+\\.\\d+),\\s*(-?\\d+\\.\\d+),\\s*(-?\\d+\\.\\d+)\\s*>");
	Match^ match = regex->Match(resp);

	GrblStatus status;
	status.isMoving = match->Groups[1]->Value->Equals("Run");
	status.x = System::Convert::ToDouble(match->Groups[2]->Value);
	status.y = System::Convert::ToDouble(match->Groups[3]->Value);
	status.z = System::Convert::ToDouble(match->Groups[4]->Value);

	return status;
}