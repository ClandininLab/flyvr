// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#pragma once

class Stimulus{
public:
	virtual ~Stimulus(){};
	virtual void Update() = 0;
	bool isDone = false;
};