/** Serial.h
 *
 * A very simple serial port control class that does NOT require MFC/AFX.
 *
 * License: This source code can be used and/or modified without restrictions.
 * It is provided as is and the author disclaims all warranties, expressed 
 * or implied, including, without limitation, the warranties of
 * merchantability and of fitness for any purpose. The user must assume the
 * entire risk of using the Software.
 *
 * @author Hans de Ruiter
 *
 * @version 0.1 -- 28 October 2008
 */

// Modified by Steven Herbst (sherbst@stanford.edu)

#pragma once

#include <string>
#include <windows.h>

typedef std::basic_string<TCHAR> tstring;

class Serial
{
private:
	HANDLE commHandle;
	COMSTAT status;
	DWORD errors;

public:
	Serial(tstring &commPortName, int bitRate);

	virtual ~Serial();

	/** Writes a NULL terminated string.
	 *
	 * @param buffer the string to send
	 *
	 * @return bool if successful
	 */
	bool write(const char *buffer);

	/** Writes a string of bytes to the serial port.
	 *
	 * @param buffer pointer to the buffer containing the bytes
	 * @param buffLen the number of bytes in the buffer
	 *
	 * @return bool if successful
	 */
	bool write(const char *buffer, size_t buffLen);

	/** Reads a string of bytes from the serial port.
	 *
	 * @param buffer pointer to the buffer to be written to
	 * @param buffLen the size of the buffer
	 * @param nullTerminate if set to true it will null terminate the string
	 *
	 * @return long the number of bytes read
	 */
	size_t read(char *buffer, size_t buffLen);

	/** Flushes everything from the serial port's read buffer
	 */
	void flush();
};
