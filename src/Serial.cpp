// Reference: http://www.webalice.it/fede.tft/serial_port/serial_port.html

// Modified by Steven Herbst (sherbst@stanford.edu)

#include "Serial.h"

Serial::Serial(std::string portName, unsigned baudRate) : io(), serial(io, portName)
{
	serial.set_option(asio::serial_port_base::baud_rate(baudRate));
}

void Serial::Write(std::string buffer)
{
	asio::write(serial, asio::buffer(buffer.c_str(), buffer.size()));
}

std::string Serial::ReadLine(void){
	//Reading data char by char, code is optimized for simplicity, not speed

	char c;
	std::string result;

	do {
		asio::read(serial, asio::buffer(&c, 1));

		if (c != '\r' && c!= '\n'){
			result += c;
		}
	} while (c != '\n');

	return result;
}