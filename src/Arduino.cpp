// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <sstream>
#include <fstream>
#include <iostream>
#include <chrono>
#include <regex>
#include <SimpleIni.h>

using namespace std::chrono;

#include "Arduino.h"

// Global variable containing the CNC move command
GrblCommand g_moveCommand = { 0, 0 };

// Global variable containing the most recent GRBL status
GrblStatus g_grblStatus;

// Mutex to manage access to move command and CNC status
std::mutex g_moveMutex, g_statusMutex;

// Global variable used to signal when serial port should close
bool killSerial = false;

// Handle used to run SerialThread
std::thread serialThread;

void StartSerialThread(){
	serialThread = std::thread(SerialThread);
}

void StopSerialThread(){
	// Kill the serial thread
	killSerial = true;

	// Wait for serial thread to finish
	serialThread.join();
}

void SerialThread(void){
	// Create the log file
	std::ofstream ofs("SerialThread.txt");
	ofs << "x (mm),y (mm),timestamp (s)\n";
	ofs.precision(8);

	// Create the GRBL board manager, passing in the serial port reference
	GrblBoard grbl;

	// Local variables to hold the status and move commands for GRBL
	GrblCommand moveCommand;

	// Continually poll GRBL status and move if desired
	while (!killSerial){
		// Read the current status
		grbl.ReadStatus();

		// Acquire lock to move command
		{
			std::unique_lock<std::mutex> lck{ g_moveMutex };

			// Copy move command to local variable
			moveCommand = g_moveCommand;

			// Reset move command to zero
			g_moveCommand.x = 0.0;
			g_moveCommand.y = 0.0;
		}

		// Run the move command if applicable
		if ((moveCommand.x != 0.0 || moveCommand.y != 0.0) && g_grblStatus.state == GrblStates::Idle){
			grbl.Move(moveCommand.x, moveCommand.y);
		}

		// Log position information
		// Get the time stamp
		auto tstamp = duration<double>(high_resolution_clock::now().time_since_epoch()).count();

		// Write CNC position to file
		ofs << std::fixed << g_grblStatus.x << "," << std::fixed << g_grblStatus.y << "," << std::fixed << tstamp << "\n";
	}
}

// Method definition for GrblBoard class
GrblBoard::GrblBoard() {
	// Read configuration parameters
	ReadSerialConfig("serial.ini");

	// Open the serial port
	arduino = std::unique_ptr<Serial>(new Serial(ComPort, BaudRate));

	// Wait for Arduino to restart
	std::cout << "Waiting for Arduino to start.\n";
	std::this_thread::sleep_for(std::chrono::seconds(2));

	// Send setup commands
	Init();

	// Home to origin before issuing G-code commands
	Home();
	WaitToStop();

	// Send G-code commands
	Config();
}

void GrblBoard::ReadSerialConfig(const char* loc){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(loc);

	// Read in values from INI file
	JogAmount = iniFile.GetDoubleValue("", "jog-amount", 1);
	MaxVel = iniFile.GetLongValue("", "max-velocity", 10000);
	MaxAcc = iniFile.GetLongValue("", "max-acceleration", 200);
	StepsPerMM_X = iniFile.GetLongValue("", "steps-per-mm-x", 40);
	StepsPerMM_Y = iniFile.GetLongValue("", "steps-per-mm-y", 40);

	// Homing options
	HomingPullOff = iniFile.GetLongValue("", "homing-pull-off", 20);
	HomingDebounce = iniFile.GetLongValue("", "homing-debounce", 250);
	HomingFeedRate = iniFile.GetLongValue("", "homing-feed-rate", 1000);
	HomingSeekRate = iniFile.GetLongValue("", "homing-seek-rate", 2000);

	// Get baud rate
	BaudRate = iniFile.GetLongValue("", "baud-rate", 400000);
	std::cout << "Using baud rate: " << BaudRate << "\n";

	// Interpret COM port name
	ComPort = iniFile.GetValue("", "com-port", "COM4");
	//ComPort = "\\\\.\\" + ComPort;
	std::cout << "Using port: " << ComPort << "\n";
}

void GrblBoard::Init(){
	// Causes stepper motor to hold position after movement
	BrakeAfterMovement();

	// Status will include running state and machine position
	SetupStatusReport();

	// number of steps per millimeter of movement
	StepsPerMM(StepsPerMM_X, GrblAxis::X);
	StepsPerMM(StepsPerMM_Y, GrblAxis::Y);

	// maximum velocity, in mm/min
	MaxVelocity(MaxVel, GrblAxis::X);
	MaxVelocity(MaxVel, GrblAxis::Y);

	// maximum acceleration, in mm/sec^2
	MaxAcceleration(MaxAcc, GrblAxis::X); 
	MaxAcceleration(MaxAcc, GrblAxis::Y); // maximum Y acceleration, in mm/sec^2

	// Set up homing
	EnableHoming();
	SetHomingPullOff(HomingPullOff);
	SetHomingDebounce(HomingDebounce);
	SetHomingFeedRate(HomingFeedRate);
	SetHomingSeekRate(HomingSeekRate);

	// Enable hard limits to protect the rig
	EnableHardLimits();
}

void GrblBoard::Config(){
	// Set all measurements to millimeters
	SetUnitMM();

	// Set maximum feed rate
	MaxFeedRate(MaxVel);

	// Use relative movement, rather than absolute
	MoveRelative();
}

void GrblBoard::StepsPerMM(int value, GrblAxis axis){
	if (axis == GrblAxis::X){
		GrblCommand(100, value);
	}
	else if (axis == GrblAxis::Y){
		GrblCommand(101, value);
	}
	else{
		throw std::runtime_error("Invalid GRBL axis.");
	}
}

void GrblBoard::MaxVelocity(int value, GrblAxis axis){
	if (axis == GrblAxis::X){
		GrblCommand(110, value);
	}
	else if (axis == GrblAxis::Y){
		GrblCommand(111, value);
	}
	else{
		throw std::runtime_error("Invalid GRBL axis.");
	}
}

void GrblBoard::MaxAcceleration(int value, GrblAxis axis){
	if (axis == GrblAxis::X){
		GrblCommand(120, value);
	}
	else if (axis == GrblAxis::Y){
		GrblCommand(121, value);
	}
	else{
		throw std::runtime_error("Invalid GRBL axis.");
	}
}

void GrblBoard::Home(){
	RawCommand("$H");
}

void GrblBoard::Reset(){
	arduino->Write("\x18");
}

void GrblBoard::GrblCommand(int key, int value){
	std::ostringstream oss;
	oss << "$" << key << "=" << value;
	RawCommand(oss.str());
}

void GrblBoard::RawCommand(std::string cmd){
	arduino->Write(cmd + "\r\n");
}

void GrblBoard::MaxFeedRate(int value){
	std::ostringstream oss;
	oss << "F" << value;
	RawCommand(oss.str());
}

void GrblBoard::Move(double X, double Y){
	std::ostringstream oss;
	oss.precision(3);
	oss << "G1X" << std::fixed << X << "Y" << std::fixed << Y << "Z" << std::fixed << 0.0;
	RawCommand(oss.str());
}

void GrblBoard::WaitToStop(){
	do {
		ReadStatus();
	} while (g_grblStatus.state != GrblStates::Idle);
}

std::string GrblBoard::GetStatusString(){
	// Query status.
	RawCommand("?");

	// Read response from GRBL	
	std::string resp;
	do {
		resp = arduino->ReadLine();
	} while (resp.find("<") != 0);

	return resp;
}

void GrblBoard::ReadStatus(){
	auto statusString = GetStatusString();
	
	// Parse response from GRBL
	// The format changed a bit between 0.9 and 1.1
	// <Idle|MPos:0.000,0.000,0.000
	std::string num = "(-?\\d+\\.\\d+)";
	std::regex pat("<(Idle|Run|Home|Alarm)\\|MPos:" + num + "," + num + "," + num);
	std::smatch match;

	if (!std::regex_search(statusString, match, pat)){
		throw std::runtime_error("GRBL returned bad status format.");
	}

	// Populate status
	GrblStatus grblStatus;

	// Parse status
	auto state = match.str(1);
	if (state == "Run"){
		grblStatus.state = GrblStates::Run;
	}
	else if (state == "Idle") {
		grblStatus.state = GrblStates::Idle;
	}
	else if (state == "Home") {
		grblStatus.state = GrblStates::Home;
	}
	else if (state == "Alarm"){
		grblStatus.state = GrblStates::Alarm;
	}
	else{
		throw std::runtime_error("Invalid GRBL state.");
	}
	
	// Parse coordinates
	grblStatus.x = std::stod(match.str(2));
	grblStatus.y = std::stod(match.str(3));
	grblStatus.z = std::stod(match.str(4));

	{
		// Acquire lock to status variable
		std::unique_lock<std::mutex> lck{ g_statusMutex };

		// Write status information
		g_grblStatus = grblStatus;
	}
}
