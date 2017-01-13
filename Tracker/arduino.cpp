#include "stdafx.h"
#include "arduino.h"

// This function takes the status query response (response to "?" command) as a string and breaks it down into useful data types.
GrblStatus parse_grbl_status(System::String^ query_response)
{
	GrblStatus grbl_status;
	System::String^ query_response_edited;

	query_response_edited = query_response->Replace("MPos:", ""); // Remove labels and punctuation in the string to make it easier to split based on delimiter
	query_response_edited = query_response_edited->Replace("<", "");
	query_response_edited = query_response_edited->Replace(">", "");

	System::String^ delimiter_str = ",";
	array<System::Char>^ delimiter = delimiter_str->ToCharArray();
	array<System::String^>^ response_array = query_response_edited->Split(delimiter);

	System::String^ state = response_array[0];
	if (state->Equals("Idle")) grbl_status.state = GRBL_STATE_IDLE;
	else if (state->Equals("Run")) grbl_status.state = GRBL_STATE_RUN;
	// TODO Implement the other states that probably won't happen

	grbl_status.x = System::Convert::ToDouble(response_array[1]);
	grbl_status.y = System::Convert::ToDouble(response_array[2]);
	grbl_status.z = System::Convert::ToDouble(response_array[3]);

	return grbl_status;
}

// Initialize Grbl settings
void initialize_grbl(System::IO::Ports::SerialPort^ arduino_port)
{
	System::String^ serial_response;

	// Disable delay between motor moves
	serial_response = arduino_tx_rx(arduino_port, "$1=255");
	System::Console::WriteLine("$1=255, " + serial_response);

	// Set status report mask, $10=1 means only return absolute position when queried, helps free up serial bandwidth
	serial_response = arduino_tx_rx(arduino_port, "$10=1"); // Status report mask
	System::Console::WriteLine("$10 = 1, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$100=40"); // X axis resolution (motor counts/mm)
	System::Console::WriteLine("$100=1.65, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$101=40"); // Y axis resolution (motor counts/mm)
	System::Console::WriteLine("$101=1.65, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$110=100000"); // X max rate (mm/min)
	System::Console::WriteLine("$110=5000, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$111=100000"); // Y max rate (mm/min)
	System::Console::WriteLine("$111=5000, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$120=2000"); // X accel (mm/s^2)
	System::Console::WriteLine("$120=500, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "$121=2000"); // Y accel (mm/s^2)
	System::Console::WriteLine("$121=500, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "F100000"); // Linear move feedrate (mm/min)
	System::Console::WriteLine("F5000, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "G21"); // Setting for units (G20 = in, G21 = mm)
	System::Console::WriteLine("G21, " + serial_response);

	serial_response = arduino_tx_rx(arduino_port, "G90"); // Setting for absolute or relative move commands (G90 = absolute, G91 = relative
	System::Console::WriteLine("G90, " + serial_response);
}


/* ARDUINO SERIAL COMMUNICATION FUNCTIONS
 These are used to transmit and receive messages to and from the Arduino via serial.
*/

// Send serial message to Arduino and return immediately (do not wait for response)
void arduino_tx(System::IO::Ports::SerialPort^ arduino, System::String^ message)
{
	arduino->WriteLine(message);
	return;
}

// Receive serial message from Arduino. Wait for message to become available until timeout in ms (timeout is infinite by default)
System::String^ arduino_rx(System::IO::Ports::SerialPort^ arduino, int timeout) // default timeout = infinite
{
	System::String^ serial_response;
	System::String^ main_response;

	arduino->ReadTimeout = timeout;
	try
	{
		do
		{
			serial_response = arduino->ReadLine();
			if (System::String::IsNullOrEmpty(main_response))
			{
				main_response = serial_response;
			}

		} while (!serial_response->Equals("ok\r") && !serial_response->Contains("error:"));
	}
	catch (System::TimeoutException^ exception)
	{
		arduino->ReadTimeout = System::IO::Ports::SerialPort::InfiniteTimeout;
		throw exception;
	}

	arduino->ReadTimeout = System::IO::Ports::SerialPort::InfiniteTimeout;
	return main_response;
}

// Send message to Arduino and wait for response until timeout (infinite by default, TODO: add in configurable timeout)
System::String^ arduino_tx_rx(System::IO::Ports::SerialPort^ arduino, System::String^ serial_message, int timeout) // default timeout = infinite
{
	// Writes message to serial port and returns the response. Clears serial buffer of subsequent "ok" or "errors" (for now)

	// TODO Error handling 

	arduino->WriteLine(serial_message);

	System::String^ serial_response;
	System::String^ main_response; // This will be the one actually returned. Won't bother returning "ok"
	do
	{
		serial_response = arduino->ReadLine();
		if (System::String::IsNullOrEmpty(main_response))
		{
			main_response = serial_response;
		}

	} while (!serial_response->Equals("ok\r") && !serial_response->Contains("error:"));

	return main_response;
}