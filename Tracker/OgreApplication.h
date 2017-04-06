// Steven Herbst
// sherbst@stanford.edu

// Modified from the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#pragma once

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

#include "timer.h"

#define DISPLAY_COUNT 3
#define DISPLAY_LIST  {1,2,3}

#define NEAR_CLIP_DIST 0.01
#define FAR_CLIP_DIST 10.0

#define WEST  0
#define NORTH 1
#define EAST  2

#define DISPLAY_WIDTH_METERS  1.1069
#define DISPLAY_HEIGHT_METERS 0.6226

#define DISPLAY_WIDTH_PIXELS 1440
#define DISPLAY_HEIGHT_PIXELS 900
#define DISPLAY_FULLSCREEN true

#define TARGET_FRAME_DURATION (1.0/120.0)

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

// Mutex to manage access to 3D graphics variables
extern HANDLE g_ogreMutex;

// Handle to manage the graphics thread
extern HANDLE g_graphicsThread;

// High-level thread management for graphics operations
void StartGraphicsThread(void);
void StopGraphicsThread(void);

// Thread used to handle graphics operations
DWORD WINAPI GraphicsThread(LPVOID lpParam);

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
	Ogre::RenderWindow* mWindows[DISPLAY_COUNT];
	Ogre::Camera* mCameras[DISPLAY_COUNT];
	Ogre::Viewport* mViewports[DISPLAY_COUNT];
	MonitorInfo mMonitors[DISPLAY_COUNT];

    // Added for Mac compatibility
    Ogre::String m_ResourcePath;
};