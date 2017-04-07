// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#pragma once

#define LOCK(m) WaitForSingleObject(m, INFINITE)
#define UNLOCK(m) ReleaseMutex(m)