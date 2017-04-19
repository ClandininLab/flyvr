// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef STIMMANAGER_H
#define STIMMANAGER_H

#include <random>
#include <vector>
#include <list>
#include <chrono>
#include <memory>

#include <SimpleIni.h>

#include "Stimulus.h"
#include "OgreApplication.h"

enum class StimManagerStates { Init, Interleave, Stimulus };

class StimManager
{
public:
	StimManager(OgreApplication &app, const std::string &stimConfigFile, const std::string &GraphicsOutputFile);
	~StimManager(void);
	void Update(Pose3D flyPose);

private:
	void PickNextStimulus(void);
	void MakeStimulus(std::string name);
	void ShuffleStimNames();

	OgreApplication &app;
	std::string stimConfigFile;
	std::string graphicsOutputFile;

	std::ofstream outFileStream;

	double iColorR, iColorG, iColorB;
	double iDuration;
	long randomSeed;

	CSimpleIniA iniFile;
	StimManagerStates state;

	std::unique_ptr<Stimulus> currentStimulus;

	std::mt19937 randomGenerator;
	std::vector<std::string>::iterator nextStimName;
	std::string currentStimName;
	std::vector<std::string> stimNames;

	std::chrono::high_resolution_clock::time_point lastTime;
};

#endif