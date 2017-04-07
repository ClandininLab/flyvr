
#include <windows.h>
#include <iostream>

#include "timer.h"

__int64 GetTimeStamp()
{
	FILETIME fileTime;
	GetSystemTimePreciseAsFileTime(&fileTime);

	ULARGE_INTEGER theTime;
	theTime.LowPart = fileTime.dwLowDateTime;
	theTime.HighPart = fileTime.dwHighDateTime;

	__int64 fileTime64Bit = theTime.QuadPart;

	return fileTime64Bit;
}
