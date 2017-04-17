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

namespace ArduinoNamespace{
	// Delay when waiting for GRBL to react to a move command
	const double GRBL_DELAY = 100e-3;

	// Variable containing the CNC move command
	std::atomic<GrblCommand> g_moveCommand;

	// Variable containing the most recent GRBL status
	std::atomic<GrblStatus> g_grblStatus;

	// Global variable used to signal when serial port should close
	bool killSerial = false;

	// Handle used to run SerialThread
	std::thread serialThread;

	// Variables used to signal when the serial thread has started up
	BoolSignal readyForSerial;

	// Variables used to signal when the rig has stopped moving
	BoolSignal isIdle;

	// Variable used to hold the name of the output file for serial thread
	std::string SerialOutputFile;
}

using namespace ArduinoNamespace;

void StartSerialThread(std::string outDir){
	std::cout << "Starting serial thread.\n";

	// Record name of file for serial output
	SerialOutputFile = outDir + "/" + "SerialThread.txt";

	serialThread = std::thread(SerialThread);

	// Wait for serial thread to be up and running
	readyForSerial.wait();
}

void StopSerialThread(){
	std::cout << "Stopping serial thread.\n";

	// Kill the serial thread
	killSerial = true;

	// Wait for serial thread to finish
	serialThread.join();
}

void GrblMoveCommand(double x, double y){
	GrblCommand moveCommand;
	moveCommand.x = x;
	moveCommand.y = y;
	moveCommand.fresh = true;
	g_moveCommand.store(moveCommand);
}

GrblStatus GetGrblStatus(void){
	return g_grblStatus.load();
}

void WaitForIdle(void){
	// Wait for previous command to take effect
	DelaySeconds(GRBL_DELAY);

	// Wait for rig to stop moving
	isIdle.wait();
}

void SerialThread(void){
	// Create the log file
	std::ofstream ofs(SerialOutputFile);
	ofs << "x (mm),y (mm),timestamp (s)\n";
	ofs.precision(8);

	// Create the GRBL board manager, passing in the serial port reference
	GrblBoard grbl;

	// Local variables to hold the status and move commands for GRBL
	GrblStatus grblStatus;
	GrblCommand moveCommand;

	// Let the main thread know that the serial thread
	std::cout << "Notifying main thread that serial communication is set up.\n";
	readyForSerial.update(true);

	TimeManager timeManager("SerialThread");
	timeManager.start();

	// Continually poll GRBL status and move if desired
	while (!killSerial){
		timeManager.tick();

		// Read the current status
		grblStatus = grbl.ReadStatus();

		// Update shared GRBL status variable
		g_grblStatus.store(grblStatus);

		// If no longer idle, signal to a waiting thread
		isIdle.update(grblStatus.state == GrblStates::Idle);

		// Load move command, reset fresh variable
		GrblCommand stale;
		stale.fresh = false;
		moveCommand = g_moveCommand.exchange(stale);

		// Run the move command if applicable
		bool canWriteRx = (grblStatus.rxBuf >= 64) ;
		bool canWritePlan = (grblStatus.planBuf > 0);
		if (moveCommand.fresh && canWriteRx && canWritePlan){
			grbl.Move(moveCommand.x, moveCommand.y);
		}

		// Format output data
		std::ostringstream oss;
		oss << std::fixed << grblStatus.x << ",";
		oss << std::fixed << grblStatus.y << ",";
		oss << std::fixed << grblStatus.tstamp;
		oss << "\n";

		// Write data to file
		ofs << oss.str();

		timeManager.waitUntil(grbl.TargetLoopDuration);
	}
}

// Method definition for GrblBoard class
GrblBoard::GrblBoard() {
	// Read configuration parameters
	ReadSerialConfig("serial.ini");

	// Open the serial port
	std::cout << "Trying to open serial port... ";
	try{
		arduino = std::unique_ptr<Serial>(new Serial(ComPort, BaudRate));
		std::cout << "success.\n";
	}
	catch (...){
		std::cout << "FAILED.\n";
		throw;
	}

	// Wait for Arduino to restart
	std::cout << "Waiting for Arduino to start.\n";
	DelaySeconds(ArduinoDelay);

	// Send setup commands
	std::cout << "Initializing GRBL variables.\n";
	Init();

	// If GRBL is in an alarm state, home to the origin
	// Home to origin before issuing G-code commands
	GrblStatus status = ReadStatus();
	if (status.state == GrblStates::Alarm){
		std::cout << "Homing GRBL.\n";
		Home();
	}

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

	// Arduino delay
	ArduinoDelay = iniFile.GetDoubleValue("", "arduino-delay", 0.1);

	// Get baud rate
	BaudRate = iniFile.GetLongValue("", "baud-rate", 400000);
	std::cout << "Using baud rate: " << BaudRate << "\n";

	// Interpret COM port name
	ComPort = iniFile.GetValue("", "com-port", "COM4");
	//ComPort = "\\\\.\\" + ComPort;
	std::cout << "Using port: " << ComPort << "\n";

	// Target loop duration
	TargetLoopDuration = iniFile.GetDoubleValue("", "target-loop-duration", 10e-3);
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

void GrblBoard::GrblCommand(int key, int value){
	std::ostringstream oss;
	oss << "$" << key << "=" << value;
	RawCommand(oss.str());
}

std::string GrblBoard::RawCommand(std::string cmd, bool newLine){
	if (newLine){
		arduino->Write(cmd + "\n");
	}
	else {
		arduino->Write(cmd);
	}
	return arduino->ReadLine();
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

	GrblStatus grblStatus;

	DelaySeconds(GRBL_DELAY);
	do {
		grblStatus = ReadStatus();
	} while (grblStatus.state != GrblStates::Idle);
}

GrblStatus GrblBoard::ReadStatus(){
	// Status to be returned
	GrblStatus grblStatus;

	// Query status.
	std::string resp = RawCommand("?", false);

	// Pattern to parse response from GRBL
	// Example: 
	// <Idle|MPos:0.000,0.000,0.000|Bf:15,128
	std::string state_str = "(Idle|Run|Home|Alarm|Jog)";
	std::string decimal = "(-?\\d+\\.\\d+)";
	std::string integer = "(\\d+)";

	// Build up the pattern
	std::string pattern = "<" + state_str;
	pattern += "\\|WPos:" + decimal + "," + decimal + "," + decimal;
	pattern += "\\|Bf:" + integer + "," + integer;
	std::regex rpat(pattern);

	// Read lines from serial port until one matches
	// Most likely, the body of the loop will never execute, since resp
	// should already contain the status report.  However, relying on this
	// fact would make the program fragile because any extra line printed
	// at any time would break this assumption.  Hence the loop.
	std::smatch match;
	while (!std::regex_search(resp, match, rpat)){
		resp = arduino->ReadLine();
	} 

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
	else if (state == "Jog"){
		grblStatus.state = GrblStates::Jog;
	}
	else{
		throw std::runtime_error("Invalid GRBL state.");
	}
	
	// Parse coordinates
	grblStatus.x = std::stod(match.str(2));
	grblStatus.y = std::stod(match.str(3));
	grblStatus.z = std::stod(match.str(4));

	// Parse buffer status
	grblStatus.planBuf = std::stoi(match.str(5));
	grblStatus.rxBuf = std::stoi(match.str(6));

	// Get timestamp
	grblStatus.tstamp = GetTimeStamp();

	// Mark status as valid
	grblStatus.valid = true;

	return grblStatus;
}
