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

// Storage of the OGRE scene configuration
extern Pose3D g_realPose, g_virtPose;

// Global variable used to signal when the Ogre3D window should close
extern bool g_kill3D;

// Global variable used to indicate when the Ogre3D engine is running
extern bool g_readyFor3D;
extern std::condition_variable g_gfxCV;

// Mutex to manage access to 3D graphics variables
extern std::mutex g_ogreMutex, g_gfxReadyMutex;

// Handle to manage the graphics thread
extern std::thread g_graphicsThread;

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
	void renderOneFrame(void);

	bool setup(void);
	void configure(void);
	bool createWindows(void);

	void chooseSceneManager(void);
	void createCameras(void);
	void createViewports(void);
	void setupResources(void);
	void loadResources(void);

	void defineMonitors(void);
	void updateProjMatrices(const Ogre::Vector3 &pe);
	void setBackground(double r, double g, double b);

	// Top-level scene management
	Ogre::Root* mRoot;
	Ogre::SceneManager* mSceneMgr;

	// Initialization variables
	Ogre::String mResourcesCfg;
	Ogre::String mPluginsCfg;
	Ogre::OverlaySystem* mOverlaySystem;

	// Per-display members
	Ogre::RenderWindow* mWindows[OgreConstants::DisplayCount];
	Ogre::Camera* mCameras[OgreConstants::DisplayCount];
	Ogre::Viewport* mViewports[OgreConstants::DisplayCount];
	MonitorInfo mMonitors[OgreConstants::DisplayCount];

	// Added for Mac compatibility
	Ogre::String m_ResourcePath;
};