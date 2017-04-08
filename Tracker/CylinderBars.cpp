// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include "Utility.h"
#include "CylinderBars.h"

#define _USE_MATH_DEFINES
#include <math.h>

using namespace CylinderConstants;

CylinderBars::CylinderBars(std::string name, OgreApplication &app, CSimpleIniA &iniFile)
	: name(name), app(app), iniFile(iniFile)
{
	Setup();
}

CylinderBars::~CylinderBars(){
	app.clear();
}

void CylinderBars::Setup(){
	numSpatialPeriod = iniFile.GetLongValue(name.c_str(), "number-of-periods", 50);
	dutyCycle = iniFile.GetDoubleValue(name.c_str(), "duty-cycle", 0.5);

	// Foreground color definition
	std::string foreColor(iniFile.GetValue(name.c_str(), "foreground-color", "1"));
	foreColorR = getColor(foreColor, ColorType::Red);
	foreColorG = getColor(foreColor, ColorType::Green);
	foreColorB = getColor(foreColor, ColorType::Blue);

	// Background color definition
	std::string backColor(iniFile.GetValue(name.c_str(), "background-color", "0"));
	backColorR = getColor(backColor, ColorType::Red);
	backColorG = getColor(backColor, ColorType::Green);
	backColorB = getColor(backColor, ColorType::Blue);

	waitBefore = iniFile.GetDoubleValue(name.c_str(), "wait-before", 0.55);
	activeDuration = iniFile.GetDoubleValue(name.c_str(), "active-duration", 5.0);
	waitAfter = iniFile.GetDoubleValue(name.c_str(), "wait-after", 0.55);

	rotationSpeed = -1.0 * M_PI / 180.0 * iniFile.GetDoubleValue(name.c_str(), "rotation-speed", 15.0);

	// Less commonly used parameters
	lightHeight = iniFile.GetDoubleValue(name.c_str(), "light-height", 1.25);
	patternRadius = iniFile.GetDoubleValue(name.c_str(), "pattern-radius", 0.8);
	panelHeight = iniFile.GetDoubleValue(name.c_str(), "panel-height", 1.25);
	panelThickness = iniFile.GetDoubleValue(name.c_str(), "panel-thickness", 0.001);

	// Background light definition
	std::string backLight(iniFile.GetValue(name.c_str(), "background-light", "0"));
	backLightR = getColor(backLight, ColorType::Red);
	backLightG = getColor(backLight, ColorType::Green);
	backLightB = getColor(backLight, ColorType::Blue);

	// Create the scene
	CreateScene();

	// Setup current state
	currentState = CylinderBarStates::Init;
}

void CylinderBars::CreateScene(void){
	// Turn on background lighting
	app.setAmbientLight(backLightR, backLightG, backLightB);

	// Create main light
	app.createLight(0, lightHeight, 0);

	// Derived scene parameters
	double dtheta = (2.0 * M_PI) / numSpatialPeriod;
	double awidth = dutyCycle * dtheta;
	double xdim = 2 * patternRadius * sin(awidth / 2.0);
	double ydim = panelHeight;
	double zdim = panelThickness;

	// Create node for all stimulus objects
	stimNode = app.createRootChild();

	// Create and attach all stimulus objects
	for (int i = 0; i < numSpatialPeriod; i++){
		// Create node for the panel
		Ogre::SceneNode *panelNode = stimNode->createChildSceneNode();

		// Apply scaling to panel
		double n = 1.0 / CubeSideLength;
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
		Ogre::Entity *panelEnt = app.createEntity("cube.mesh");
		panelNode->attachObject(panelEnt);

		// Set the panel color to the desired value
		// TODO: is there a better way to set the color of a panel?
		Ogre::ColourValue panelColor = Ogre::ColourValue(foreColorR, foreColorG, foreColorB);
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
