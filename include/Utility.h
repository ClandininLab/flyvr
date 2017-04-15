// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef UTILITY_H
#define UTILITY_H

#include <chrono>
#include <iostream>
#include <thread>
#include <string>
#include <mutex>
#include <condition_variable>

enum class ColorType {Red, Green, Blue};

double getColor(std::string s, ColorType t);

void DelaySeconds(double t);

double GetTimeStamp();

class BoolSignal{
public:
	BoolSignal() : statusBool(false) {}
	void update(bool value);
	void wait();
private:
	bool statusBool;
	std::mutex statusMutex;
	std::condition_variable statusCV;
};

class TimeManager{
public:
	TimeManager(std::string name);
	void start(void);
	void tick(void);
	void waitUntil(double targetLoopDuration);
	double totalDuration();
private:
	std::string name;
	std::chrono::time_point<std::chrono::high_resolution_clock> startTime;
	std::chrono::time_point<std::chrono::high_resolution_clock> loopStart;
};

#endif