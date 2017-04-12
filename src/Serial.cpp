/** Serial.cpp
 *
 * A very simple serial port control class that does NOT require MFC/AFX.
 *
 * @author Hans de Ruiter
 *
 * @version 0.1 -- 28 October 2008
 */

// Modified by Steven Herbst (sherbst@stanford.edu)

#include <iostream>

#include "Serial.h"

Serial::Serial(tstring &commPortName, int bitRate)
{
	commHandle = CreateFile(commPortName.c_str(), 
		GENERIC_READ|GENERIC_WRITE, 
		0, 
		NULL, 
		OPEN_EXISTING, 
		FILE_ATTRIBUTE_NORMAL,
		NULL);

	if(commHandle == INVALID_HANDLE_VALUE) 
	{
		throw std::runtime_error("Failed to open serial port");
	}

	// Set serial options
	DCB dcb = { 0 };
	if (!GetCommState(commHandle, &dcb)){
		throw std::runtime_error("Failed to get serial parameters.");
	}

	// Main contents of dcb
	dcb.BaudRate = bitRate;
	dcb.ByteSize = 8;
	dcb.StopBits = ONESTOPBIT;
	dcb.Parity = NOPARITY;

	//Setting the DTR to Control_Enable ensures that the Arduino is properly
	//reset upon establishing a connection
	dcb.fDtrControl = DTR_CONTROL_ENABLE;

	//Set the parameters and check for their proper application
	if (!SetCommState(commHandle, &dcb))
	{
		throw std::runtime_error("Failed to set serial parameters.");
	}

	//Flush any remaining characters in the buffers
	flush();
}

Serial::~Serial()
{
	CloseHandle(commHandle);
}

bool Serial::write(const char *buffer)
{
	return write(buffer, strlen(buffer));
}

bool Serial::write(const char *buffer, size_t buffLen)
{
	DWORD numWritten;

	if (!WriteFile(commHandle, buffer, (DWORD)buffLen, &numWritten, NULL)){
		ClearCommError(commHandle, &errors, &status);
		return false;
	}

	return true;
}

size_t Serial::read(char *buffer, size_t buffLen)
{
	//Number of bytes we'll have read
	DWORD numRead;
	//Number of bytes we'll really ask to read
	DWORD toRead;

	//Use the ClearCommError function to get status info on the Serial port
	ClearCommError(commHandle, &errors, &status);

	if (status.cbInQue > 0)
	{
		if (status.cbInQue>buffLen)
		{
			toRead = (DWORD)buffLen;
		}
		else
		{
			toRead = status.cbInQue;
		}

		//Try to read the require number of chars, and return the number of read bytes on success
		if (ReadFile(commHandle, buffer, toRead, &numRead, NULL))
		{
			return numRead;
		}
	}

	//If nothing has been read, or that an error was detected return 0
	return 0;
}

void Serial::flush()
{
	PurgeComm(commHandle, PURGE_RXCLEAR | PURGE_TXCLEAR);
}
