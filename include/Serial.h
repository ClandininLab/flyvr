// Reference: http://www.webalice.it/fede.tft/serial_port/serial_port.html

// Modified by Steven Herbst (sherbst@stanford.edu)

#ifndef SERIAL_H
#define SERIAL_H

#include <asio.hpp>
#include <string>

class Serial
{
public:
	// Constructor accepts port name (e.g., "COM4") and baud rate (e.g., 400000)
	Serial(std::string portName, unsigned baudRate);

	// Writes string to serial terminal, returns true if successful, false otherwise
	void Write(std::string buffer);

	// Reads a single line from serial terminal
	std::string ReadLine();

private:
	asio::io_service io;
	asio::serial_port serial;
};

#endif