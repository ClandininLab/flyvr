// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#ifndef CYLINDERBARS_H
#define CYLINDERBARS_H

#include <string>
#include <chrono>

#include <SimpleIni.h>

#include "OgreApplication.h"
#include "Stimulus.h"

enum class CylinderBarStates { Init, WaitBefore, Active, WaitAfter };

class CylinderBars : public Stimulus{
public:
	CylinderBars(std::string name, OgreApplication &app, CSimpleIniA &iniFile);
	~CylinderBars();
	std::string Update(Pose3D flyPose);
private:
	void Setup(void);
	void CreateScene(void);

	std::string name;
	OgreApplication &app;
	CSimpleIniA &iniFile;

	Ogre::SceneNode *stimNode;

	CylinderBarStates currentState;

	std::chrono::high_resolution_clock::time_point lastTime;

	long numSpatialPeriod;
	double dutyCycle;

	double foreColorR;
	double foreColorG;
	double foreColorB;

	double backColorR;
	double backColorG;
	double backColorB;

	double waitBefore;
	double activeDuration;
	double waitAfter;

	double rotationSpeed;

	double patternRadius;
	double panelHeight;
	double panelThickness;

	bool closedLoop;
};

#endif