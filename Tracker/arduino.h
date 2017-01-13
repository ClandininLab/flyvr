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
