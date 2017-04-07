// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#pragma once

class Stimulus{
	public:
		virtual ~Stimulus(){};
		virtual void Setup() = 0;
		virtual void Update() = 0;
		virtual void Destroy() = 0;
		bool isDone = false;
};