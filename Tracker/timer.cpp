#include "stdafx.h"

#include <windows.h>

#include "timer.h"

DebugTimer::DebugTimer(String^ fileName){
	fileStream = gcnew StreamWriter(fileName);
}

void DebugTimer::Close(){
	fileStream->Close();
}

// start of code modified from http://stackoverflow.com/questions/1739259/how-to-use-queryperformancecounter
void DebugTimer::Tick()
{
	LARGE_INTEGER li;

	// Record CPU frequency
	if (!QueryPerformanceFrequency(&li))
		Console::WriteLine("QueryPerformanceFrequency failed!");
	PCFreq = double(li.QuadPart) / 1000.0;

	// Record start time
	QueryPerformanceCounter(&li);
	CounterStart = li.QuadPart;
}
void DebugTimer::Tock(){
	Tock("{0:0.000}");
}
void DebugTimer::Tock(String^ format)
{
	LARGE_INTEGER li;
	double duration;

	// Record duration
	QueryPerformanceCounter(&li);
	duration = double(li.QuadPart - CounterStart) / PCFreq;

	// Write duration to file
	fileStream->WriteLine(format, duration);
}
// end of code modified from http://stackoverflow.com/questions/1739259/how-to-use-queryperformancecounter
