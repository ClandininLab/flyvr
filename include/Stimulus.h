// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef STIMULUS_H
#define STIMULUS_H

class Stimulus{
public:
	virtual ~Stimulus(){};
	virtual void Update() = 0;
	bool isDone = false;
};

#endif