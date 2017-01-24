#ifndef TIMER_H
#define TIMER_H

using namespace System;
using namespace System::IO;

public ref class DebugTimer
{
public:
	double PCFreq = 0.0;
	__int64 CounterStart = 0;
	StreamWriter^ fileStream;
	DebugTimer(System::String^ fileName);
	void Tick();
	void Tock(System::String^ format);
	void Tock();
	void Close();
};

#endif
