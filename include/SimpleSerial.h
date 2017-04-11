// Modified from: http://www.webalice.it/fede.tft/serial_port/serial_port.html

#pragma once

#include <boost/asio.hpp>

class SimpleSerial
{
public:
	SimpleSerial(std::string port, unsigned int baud_rate);
	void writeString(std::string s);
	std::string readLine(void);
	
private:
	boost::asio::io_service io;
	boost::asio::serial_port serial;
};