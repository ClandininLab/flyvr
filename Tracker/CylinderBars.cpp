#include "stdafx.h"

#include "CylinderBars.h"

#define _USE_MATH_DEFINES
#include <math.h>

CylinderBars::CylinderBars(std::string name, OgreApplication &app, CSimpleIniA &iniFile)
	: name(name), app(app), iniFile(iniFile)
{

}

CylinderBars::~CylinderBars(){

}

void CylinderBars::Setup(){
	numSpatialPeriod = iniFile.GetLongValue(name.c_str(), "number-of-periods");
	dutyCycle = iniFile.GetDoubleValue(name.c_str(), "duty-cycle");

	// TODO: allow interpretation of foreground color as monochrome double or RGB hex
	foreColorR = iniFile.GetDoubleValue(name.c_str(), "foreground-color");
	foreColorG = iniFile.GetDoubleValue(name.c_str(), "foreground-color");
	foreColorB = iniFile.GetDoubleValue(name.c_str(), "foreground-color");

	// TODO: allow interpretation of foreground color as monochrome double or RGB hex
	backColorR = iniFile.GetDoubleValue(name.c_str(), "background-color");
	backColorG = iniFile.GetDoubleValue(name.c_str(), "background-color");
	backColorB = iniFile.GetDoubleValue(name.c_str(), "background-color");

	waitBefore = iniFile.GetDoubleValue(name.c_str(), "wait-before");
	activeDuration = iniFile.GetDoubleValue(name.c_str(), "active-duration");
	waitAfter = iniFile.GetDoubleValue(name.c_str(), "wait-after");

	rotationSpeed = -1.0 * M_PI / 180.0 * iniFile.GetDoubleValue(name.c_str(), "rotation-speed");

	// Less commonly used parameters
	lightHeight = iniFile.GetDoubleValue(name.c_str(), "light-height", 1.25);
	patternRadius = iniFile.GetDoubleValue(name.c_str(), "pattern-radius", 0.8);
	panelHeight = iniFile.GetDoubleValue(name.c_str(), "panel-height", 1.25);
	panelThickness = iniFile.GetDoubleValue(name.c_str(), "panel-thickness", 0.001);

	// TODO: allow for RGB interpretation of background light
	backLightR = iniFile.GetDoubleValue(name.c_str(), "background-light", 0);
	backLightG = iniFile.GetDoubleValue(name.c_str(), "background-light", 0);
	backLightB = iniFile.GetDoubleValue(name.c_str(), "background-light", 0);

	// Create the scene
	CreateScene();

	// Setup current state
	currentState = CylinderBarStates::Init;
}

void CylinderBars::CreateScene(void){
	// Create nodes for the whole scene and stimulus part
	Ogre::SceneNode *rootNode = app.mSceneMgr->getRootSceneNode();
	stimNode = rootNode->createChildSceneNode();

	// Turn on background lighting
	app.mSceneMgr->setAmbientLight(Ogre::ColourValue(backLightR, backLightG, backLightB));

	// Create main light
	Ogre::Light *light = app.mSceneMgr->createLight("MainLight");
	light->setPosition(0.0, Ogre::Real(lightHeight), 0);
	rootNode->attachObject(light);

	// Derived scene parameters
	double dtheta = (2.0 * M_PI) / numSpatialPeriod;
	double awidth = dutyCycle * dtheta;
	double xdim = 2 * patternRadius * sin(awidth / 2.0);
	double ydim = panelHeight;
	double zdim = panelThickness;

	for (int i = 0; i < numSpatialPeriod; i++){
		// Create node for the panel
		Ogre::SceneNode* panelNode = stimNode->createChildSceneNode();

		// Apply scaling to panel
		double n = 1.0/CUBE_SIDE_LENGTH;
		panelNode->setScale(Ogre::Real(xdim*n), Ogre::Real(ydim*n), Ogre::Real(zdim*n));

		// Calculate angular position of this panel
		double theta = i*dtheta;

		// Apply position to panel
		double xpos = patternRadius * sin(theta);
		double ypos = 0.0;
		double zpos = -patternRadius * cos(theta);
		panelNode->setPosition(Ogre::Vector3(xpos, ypos, zpos));

		// Apply rotation to panel
		double pitch = 0.0;
		double yaw = -theta;
		double roll = 0.0;
		panelNode->pitch(Ogre::Radian(pitch));
		panelNode->yaw(Ogre::Radian(yaw));
		panelNode->roll(Ogre::Radian(roll));

		// Attach the cube mesh to the panel
		Ogre::Entity* panelEnt = app.mSceneMgr->createEntity("cube.mesh");
		panelNode->attachObject(panelEnt);

		// Set the panel color to the desired value
		Ogre::ColourValue panelColor = Ogre::ColourValue(foreColorR, foreColorG, foreColorB);

		// TODO: is there a better way to set the color of a panel?
		panelEnt->getSubEntity(0)->getMaterial().getPointer()->getTechnique(0)->getPass(0)->setDiffuse(panelColor);
	}
}

void CylinderBars::Update(){
	if (currentState == CylinderBarStates::Init){
		lastTime = std::chrono::high_resolution_clock::now();
		app.setBackground(backColorR, backColorG, backColorB);
		currentState = CylinderBarStates::WaitBefore;
	}
	else if (currentState == CylinderBarStates::WaitBefore){
		auto thisTime = std::chrono::high_resolution_clock::now();
		auto duration = std::chrono::duration<double>(thisTime - lastTime).count();
		if (duration >= waitBefore){
			lastTime = std::chrono::high_resolution_clock::now();
			currentState = CylinderBarStates::Active;
		}
	}
	else if (currentState == CylinderBarStates::Active){
		auto thisTime = std::chrono::high_resolution_clock::now();
		auto duration = std::chrono::duration<double>(thisTime - lastTime).count();

		double rot = duration * rotationSpeed;
		stimNode->setOrientation(Ogre::Quaternion(Ogre::Radian(rot), Ogre::Vector3(0, 1, 0)));

		if (duration >= activeDuration){
			lastTime = std::chrono::high_resolution_clock::now();
			currentState = CylinderBarStates::WaitAfter;
		}
	}
	else if (currentState == CylinderBarStates::WaitAfter){
		auto thisTime = std::chrono::high_resolution_clock::now();
		auto duration = std::chrono::duration<double>(thisTime - lastTime).count();

		if (duration >= waitAfter){
			isDone = true;
		}
	}
	else {
		throw std::exception("Invalid CylinderBar state.");
	}
}

void CylinderBars::Destroy(){
	app.mSceneMgr->clearScene();
}
