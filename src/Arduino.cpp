// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <sstream>
#include <fstream>
#include <iostream>
#include <chrono>
#include <SimpleIni.h>

using namespace std::chrono;

#include "Arduino.h"
#include "Utility.h"

// Delay when waiting for GRBL to react to a move command
const double GRBL_DELAY = 100e-3;

// Delay when waiting for Arduino to start up
const double ARDUINO_DELAY = 2.0;

// Variable containing the CNC move command
GrblCommand g_moveCommand = { 0, 0, false };

// Variable containing the most recent GRBL status
GrblStatus g_grblStatus;

// Mutex to manage access to move command
std::mutex moveMutex;

// Mutex to manage access to status
std::mutex statusMutex;

// Global variable used to signal when serial port should close
bool killSerial = false;

// Handle used to run SerialThread
std::thread serialThread;

// Variables used to signal when the serial thread has started up
bool readyForSerial = false;
std::mutex serReadyMutex;
std::condition_variable serCV;

// Variables used to signal when the rig has stopped moving
bool isIdle = false;
std::mutex idleMutex;
std::condition_variable idleCV;

void StartSerialThread(){
	std::cout << "Starting serial thread.\n";

	serialThread = std::thread(SerialThread);

	// Wait for serial thread to be up and running
	std::unique_lock<std::mutex> lck(serReadyMutex);
	serCV.wait(lck, []{return readyForSerial; });
}

void StopSerialThread(){
	std::cout << "Stopping serial thread.\n";

	// Kill the serial thread
	killSerial = true;

	// Wait for serial thread to finish
	serialThread.join();
}

void GrblMoveCommand(double x, double y){
	std::unique_lock<std::mutex> lck{ moveMutex };

	g_moveCommand.x = x;
	g_moveCommand.y = y;
	g_moveCommand.fresh = true;
}

GrblStatus GetGrblStatus(void){
	std::unique_lock<std::mutex> lck{ statusMutex };

	return g_grblStatus;
}

void WaitForIdle(void){
	// Wait for previous command to take effect
	DelaySeconds(GRBL_DELAY);

	// Wait for rig to stop moving
	std::unique_lock<std::mutex> lck(idleMutex);
	idleCV.wait(lck, []{return isIdle; });
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

	// Let the main thread know that the serial thread
	std::cout << "Notifying main thread that serial communication is set up.\n";
	{
		std::lock_guard<std::mutex> lck(serReadyMutex);
		readyForSerial = true;
	}
	serCV.notify_one();

	// Continually poll GRBL status and move if desired
	while (!killSerial){
		// Read the current status
		grbl.ReadStatus();

		// If no longer idle, signal to a waiting thread
		{
			std::lock_guard<std::mutex> lck(idleMutex);
			isIdle = (g_grblStatus.state == GrblStates::Idle);
		}
		if (isIdle){
			idleCV.notify_one();
		}

		// Acquire lock to move command
		{
			std::unique_lock<std::mutex> lck{ moveMutex };

			// Copy move command to local variable
			moveCommand = g_moveCommand;

			// Reset move command to zero
			g_moveCommand.fresh = false;
		}

		// Run the move command if applicable
		if (moveCommand.fresh && g_grblStatus.state == GrblStates::Idle){
			grbl.Move(moveCommand.x, moveCommand.y);
		}

		// Format output data
		std::ostringstream oss;
		oss << std::fixed << g_grblStatus.x << ",";
		oss << std::fixed << g_grblStatus.y << ",";
		oss << std::fixed << g_grblStatus.tstamp;
		oss << "\n";

		// Write data to file
		ofs << oss.str();
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
	DelaySeconds(ARDUINO_DELAY);

	// Send setup commands
	std::cout << "Initializing GRBL variables.\n";
	Init();

	// Home to origin before issuing G-code commands
	// This is a blocking command that returns after homing is complete
	std::cout << "Homing GRBL.\n";
	Home();

	// Send G-code commands
	std::cout << "Sending G-Code configuration.\n";
	Config();
}

void GrblBoard::ReadSerialConfig(const char* loc){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(loc);

	// Read in values from INI file
	MaxVel = iniFile.GetLongValue("", "max-velocity", 10000);
	MaxAcc = iniFile.GetLongValue("", "max-acceleration", 200);
	StepsPerMM_X = iniFile.GetLongValue("", "steps-per-mm-x", 40);
	StepsPerMM_Y = iniFile.GetLongValue("", "steps-per-mm-y", 40);

	// Homing options
	HomingPullOff = iniFile.GetLongValue("", "homing-pull-off", 20);
	HomingDebounce = iniFile.GetLongValue("", "homing-debounce", 250);
	HomingFeedRate = iniFile.GetLongValue("", "homing-feed-rate", 1000);
	HomingSeekRate = iniFile.GetLongValue("", "homing-seek-rate", 2000);

	// Soft limits
	MaxTravelX = iniFile.GetDoubleValue("", "max-travel-x", 600);
	MaxTravelY = iniFile.GetDoubleValue("", "max-travel-y", 600);

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
	MoveAbsolute();
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
	WaitToStop();
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
	if (-MaxTravelX <= X && X <= -HomingPullOff &&
		-MaxTravelY <= Y && Y <= -HomingPullOff){

		std::ostringstream oss;
		oss.precision(3);
		oss << "G1X" << std::fixed << X << "Y" << std::fixed << Y;
		RawCommand(oss.str());
	}
}

void GrblBoard::WaitToStop(){
	// Wait for previous command to take effect

	DelaySeconds(GRBL_DELAY);
	do {
		ReadStatus();
	} while (g_grblStatus.state != GrblStates::Idle);
}

void GrblBoard::ReadStatus(){
	// Query status.
	RawCommand("?");

	// Pattern to parse response from GRBL
	// Example: 
	// <Idle|MPos:0.000,0.000,0.000
	std::string num = "(-?\\d+\\.\\d+)";
	std::regex pat("<(Idle|Run|Home|Alarm)\\|MPos:" + num + "," + num + "," + num);

	// Read lines from serial port until one matches
	std::string resp;
	std::smatch match;
	do {
		resp = arduino->ReadLine();
		//std::cout << "resp: " << resp << "\n";
	} while (!std::regex_search(resp, match, pat));

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

	// Get timestamp
	grblStatus.tstamp = GetTimeStamp();

	{
		// Acquire lock to status variable
		std::unique_lock<std::mutex> lck{ statusMutex };

		// Write status information
		g_grblStatus = grblStatus;
	}
}
