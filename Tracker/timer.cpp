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
	if (!QueryPerformanceFrequency(&li))
		Console::WriteLine("QueryPerformanceFrequency failed!");

	PCFreq = double(li.QuadPart) / 1000.0;

	QueryPerformanceCounter(&li);
	CounterStart = li.QuadPart;
}
void DebugTimer::Tock()
{
	LARGE_INTEGER li;
	QueryPerformanceCounter(&li);
	fileStream->WriteLine(double(li.QuadPart - CounterStart) / PCFreq);
}
// end of code modified from http://stackoverflow.com/questions/1739259/how-to-use-queryperformancecounter
