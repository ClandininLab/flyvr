// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef STIMULUS_H
#define STIMULUS_H

#include "OgreApplication.h"

class Stimulus{
public:
	virtual ~Stimulus(){};
	// TODO: accept position of fly 
	virtual void Update(Pose3D flyPose) = 0;
	// TODO: add method to output per-frame information from stimulus
	bool isDone = false;
};

#endif