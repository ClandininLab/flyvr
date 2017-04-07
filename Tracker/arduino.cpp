#include <windows.h>
#include <iostream>

using namespace System;
using namespace System::IO;
using namespace System::IO::Ports;
using namespace System::Text::RegularExpressions;

#include "arduino.h"
#include "timer.h"
#include "mutex.h"

// Global variable instantiations
GrblCommand g_moveCommand = { 0, 0 };
GrblStatus g_grblStatus;
bool g_killSerial = false;
HANDLE g_moveMutex, g_statusMutex;
HANDLE g_serialThread;

void StartSerialThread(){
	DWORD serThreadID;
	g_moveMutex = CreateMutex(NULL, FALSE, NULL);
	g_statusMutex = CreateMutex(NULL, FALSE, NULL);
	g_serialThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)SerialThread, NULL, 0, &serThreadID);
}

void StopSerialThread(){
	// Kill the serial thread
	g_killSerial = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(g_serialThread, INFINITE);

	// Close the handles to the mutexes and serial thread
	CloseHandle(g_serialThread);
	CloseHandle(g_moveMutex);
	CloseHandle(g_statusMutex);
}

DWORD WINAPI SerialThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);

	// Create the timer
	StreamWriter^ logger = gcnew StreamWriter("SerialThread.txt");
	logger->WriteLine("x (mm),y (mm),timestamp (100ns)");

	GrblBoard ^grbl;
	GrblStatus status;
	GrblCommand moveCommand;

	// Connect to GRBL
	grbl = gcnew GrblBoard();

	// Continually poll GRBL status and move if desired
	while (!g_killSerial){
		// Read the current status
		grbl->ReadStatus();

		LOCK(g_moveMutex);
			// Copy move command to local variable
			moveCommand = g_moveCommand;

			// Reset move command to zero
			g_moveCommand.x = 0.0;
			g_moveCommand.y = 0.0;
		UNLOCK(g_moveMutex);

		// Run the move command if applicable
		if ((moveCommand.x != 0.0 || moveCommand.y != 0.0) && !g_grblStatus.isMoving){
			grbl->Move(moveCommand.x, moveCommand.y);
		}

		// Log position information
		// Get the time stamp
		__int64 tstamp = GetTimeStamp();

		// Format the data output
		String^ data = String::Format(
			"{0:0.000},{1:0.000},{2}",
			g_grblStatus.x,
			g_grblStatus.y,
			tstamp);

		logger->WriteLine(data);
	}

	// Close streams
	logger->Close();
	grbl->Close();

	return TRUE;
}

// Method definition for GrblBoard class
GrblBoard::GrblBoard(){
	arduino = gcnew SerialPort(GRBL_COM_PORT, GRBL_BAUD_RATE);
	arduino->Open();
	Init();
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

void GrblBoard::Close(){
	arduino->Close();
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

void GrblBoard::ReadStatus(){
	// Query status.
	arduino->DiscardInBuffer();
	arduino->WriteLine("?");

	// Read response from GRBL
	String^ resp = arduino->ReadLine();
	while (!resp->StartsWith("<")){
		resp = arduino->ReadLine();
	}

	// Parse response from GRBL
	// The format changed a bit between 0.9 and 1.1
	// <Idle|MPos:0.000,0.000,0.000
	Regex^ regex = gcnew Regex("<(Idle|Run)\\|MPos:(-?\\d+\\.\\d+),(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)");
	Match^ match = regex->Match(resp);

	bool isMoving = match->Groups[1]->Value->Equals("Run");
	double x = System::Convert::ToDouble(match->Groups[2]->Value);
	double y = System::Convert::ToDouble(match->Groups[3]->Value);
	double z = System::Convert::ToDouble(match->Groups[4]->Value);

	LOCK(g_statusMutex);
		g_grblStatus.isMoving = isMoving;
		g_grblStatus.x = x;
		g_grblStatus.y = y;
		g_grblStatus.z = z;
	UNLOCK(g_statusMutex);
}