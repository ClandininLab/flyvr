// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef UTILITY_H
#define UTILITY_H

#include <iostream>
#include <thread>
#include <string>

enum class ColorType {Red, Green, Blue};

double getColor(std::string s, ColorType t);

void DelaySeconds(double t);

double GetTimeStamp();

#endif