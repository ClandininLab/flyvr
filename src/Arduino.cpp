// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <sstream>
#include <fstream>
#include <iostream>
#include <chrono>
#include <regex>

using namespace std::chrono;

#include "Arduino.h"

// Global variable instantiations
GrblCommand g_moveCommand = { 0, 0 };
GrblStatus g_grblStatus;
bool g_killSerial = false;

void StartSerialThread(){
	g_serialThread = std::thread(SerialThread);
}

void StopSerialThread(){
	// Kill the serial thread
	g_killSerial = true;

	// Wait for serial thread to finish
	g_serialThread.join();
}

void SerialThread(void){
	// Create the timer
	std::ofstream ofs("SerialThread.txt");
	ofs << "x (mm),y (mm),timestamp (100ns)";
	ofs.precision(8);

	// Create the serial port
	SimpleSerial arduino = SimpleSerial(GRBL_COM_PORT, GRBL_BAUD_RATE);

	// Create the GRBL board manager, passing in the serial port reference
	GrblBoard grbl(&arduino);

	// Local variables to hold the status and move commands for GRBL
	GrblStatus status;
	GrblCommand moveCommand;

	// Continually poll GRBL status and move if desired
	while (!g_killSerial){
		// Read the current status
		grbl.ReadStatus();

		// Acquire lock to move command
		std::unique_lock<std::mutex> lck{ g_moveMutex };

		// Copy move command to local variable
		moveCommand = g_moveCommand;

		// Reset move command to zero
		g_moveCommand.x = 0.0;
		g_moveCommand.y = 0.0;

		// Unlock move command
		lck.unlock();

		// Run the move command if applicable
		if ((moveCommand.x != 0.0 || moveCommand.y != 0.0) && !g_grblStatus.isMoving){
			grbl.Move(moveCommand.x, moveCommand.y);
		}

		// Log position information
		// Get the time stamp
		auto tstamp = duration<double>(high_resolution_clock::now().time_since_epoch()).count();

		// Write CNC position to file
		ofs << g_grblStatus.x << "," << g_grblStatus.y << "," << tstamp;
	}
}

// Method definition for GrblBoard class
GrblBoard::GrblBoard(SimpleSerial *arduino) : arduino(arduino){
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
	arduino->writeString("\x18");
}

void GrblBoard::GrblCommand(int key, int value){
	std::ostringstream oss;
	oss << "$" << key << "=" << value;
	RawCommand(oss.str());
}

void GrblBoard::RawCommand(std::string cmdString){
	arduino->writeString(cmdString + "\r\n");
}

void GrblBoard::MaxFeedRate(int value){
	std::ostringstream oss;
	oss << "F" << value;
	RawCommand(oss.str());
}

void GrblBoard::Move(double X, double Y){
	std::ostringstream oss;
	oss.precision(3);
	oss << "G1X" << X << "Y" << Y;
	RawCommand(oss.str());
}

void GrblBoard::ReadStatus(){
	// Query status.
	// arduino->DiscardInBuffer();
	RawCommand("?");

	// Read response from GRBL
	std::string resp = arduino->readLine();
	while (resp.find("<") != 0){
		resp = arduino->readLine();
	}

	// Parse response from GRBL
	// The format changed a bit between 0.9 and 1.1
	// <Idle|MPos:0.000,0.000,0.000
	std::string num = "(-?\\d+\\.\\d+)";
	std::regex pat("<(Idle|Run)\\|MPos:" + num + "," + num + "," + num);
	std::smatch match;

	if (!std::regex_search(resp, match, pat)){
		throw std::runtime_error("GRBL returned bad status format.");
	}

	bool isMoving = (match.str(1) == "Run");
	double x = std::stod(match.str(2));
	double y = std::stod(match.str(3));
	double z = std::stod(match.str(4));

	// Acquire lock to status variable
	std::unique_lock<std::mutex> lck{ g_statusMutex };

	// Write status information
	g_grblStatus.isMoving = isMoving;
	g_grblStatus.x = x;
	g_grblStatus.y = y;
	g_grblStatus.z = z;

	// Unlock status variable
	lck.unlock();
}
