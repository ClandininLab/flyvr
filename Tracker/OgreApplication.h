// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

// OgreApplication is based on the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#pragma once

#include <mutex>
#include <thread>
#include <condition_variable>

#include <OgreCamera.h>
#include <OgreEntity.h>
#include <OgreLogManager.h>
#include <OgreRoot.h>
#include <OgreViewport.h>
#include <OgreSceneManager.h>
#include <OgreRenderWindow.h>
#include <OgreConfigFile.h>
#include <SdkTrays.h>
#include <OgreNode.h>

#include <OgreOverlaySystem.h>

namespace OgreConstants{
	const unsigned DisplayCount = 3;
	const unsigned DisplayList[] = { 1, 2, 3 };

	const unsigned West = 0;
	const unsigned North = 1;
	const unsigned East = 2;
	
	const double DisplayWidthMeters = 1.1069;
	const double DisplayHeightMeters = 0.6226;

	const double NearClipDist = 0.01; // meters
	const double FarClipDist = 10.0; // meters

	const unsigned DisplayWidthPixels = 1440;
	const unsigned DisplayHeightPixels = 900;
	const bool DisplayFullscreen = true;

	const double TargetLoopDuration = 1.0 / 120.0;
}

// Struct to keep track of the user's real position and virtual position
struct Pose3D{
	double x, y, z;
	double pitch, yaw, roll;
};

// Used to keep track of monitors information
struct MonitorInfo{
	Ogre::Vector3 pa;
	Ogre::Vector3 pb;
	Ogre::Vector3 pc;
};

// Global variables used to manage access to real and virtual viewer position
extern std::mutex g_ogreMutex;
extern Pose3D g_realPose, g_virtPose;

// High-level thread management for graphics operations
void StartGraphicsThread(void);
void StopGraphicsThread(void);

// Thread used to handle graphics operations
void GraphicsThread(void);

class OgreApplication
{
public:
	OgreApplication(void);
	~OgreApplication(void);

	void go(void);
	
	void setRootPos(double x, double y, double z);
	void setRootRot(double pitch, double yaw, double roll);
	void updateProjMatrices(double x, double y, double z);

	void createLight(double x, double y, double z);
	void setAmbientLight(double r, double g, double b);
	void setBackground(double r, double g, double b);

	void renderOneFrame(void);
	void clear(void);

	Ogre::SceneNode* createRootChild(void);
	Ogre::Entity* createEntity(std::string meshName);

private:

	bool setup(void);
	void configure(void);
	bool createWindows(void);

	void chooseSceneManager(void);
	void createCameras(void);
	void createViewports(void);
	void setupResources(void);
	void loadResources(void);

	void defineMonitors(void);

	// Top-level scene management
	Ogre::Root *mRoot;
	Ogre::SceneManager *mSceneMgr;

	// Initialization variables
	Ogre::String mResourcesCfg;
	Ogre::String mPluginsCfg;
	Ogre::OverlaySystem *mOverlaySystem;

	// Per-display members
	Ogre::RenderWindow *mWindows[OgreConstants::DisplayCount];
	Ogre::Camera *mCameras[OgreConstants::DisplayCount];
	Ogre::Viewport *mViewports[OgreConstants::DisplayCount];
	MonitorInfo mMonitors[OgreConstants::DisplayCount];

	// Added for Mac compatibility
	Ogre::String mResourcePath;
};