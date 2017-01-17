using namespace System;
using namespace System::IO::Ports;

public ref class GrblBoard
{
public:
	SerialPort^ arduino;
	GrblBoard(SerialPort^ arduino);
	void Init();
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
	bool IsMoving();
};

// Stuff for storing grbl status upon query command ("?")
public value struct GrblStatus
{
	int state=-1; // See Grbl states for enumerated values
	
	// Positions in working units
	double x;
	double y;
	double z; // Unused but eh, the data is there
} ;

// Grbl states
static const int GRBL_STATE_IDLE = 1;
static const int GRBL_STATE_RUN = 2;
//TODO add the rest of the states that probably won't happen

GrblStatus parse_grbl_status(System::String^ query_response);


// Arduino/Grbl initialization
void initialize_grbl(System::IO::Ports::SerialPort^ arduino_port);

/* ARDUINO SERIAL COMMUNICATION FUNCTIONS
These are used to transmit and receive messages to and from the Arduino via serial.
*/
void arduino_tx(System::IO::Ports::SerialPort^ arduino, System::String^ message);
System::String^ arduino_rx(System::IO::Ports::SerialPort^ arduino, int timeout = System::IO::Ports::SerialPort::InfiniteTimeout);
System::String^ arduino_tx_rx(System::IO::Ports::SerialPort^ arduino, System::String^ serial_message, int timeout = System::IO::Ports::SerialPort::InfiniteTimeout);
