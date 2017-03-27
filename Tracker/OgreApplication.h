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

#include <OgreOverlaySystem.h>

#define DISPLAY_COUNT 3
#define DISPLAY_LIST  {1,2,3}

#define PATTERN_RADIUS 222
#define PANEL_THICKNESS 1
#define PANEL_HEIGHT 200
#define PANEL_COUNT 100

#define WEST  1
#define NORTH 0
#define EAST  2

#define DISPLAY_WIDTH_METERS 1.10690093 
#define DISPLAY_HEIGHT_METERS 0.6226317743326399

#define DISPLAY_WIDTH_PIXELS 1600
#define DISPLAY_HEIGHT_PIXELS 900
#define DISPLAY_FULLSCREEN true

// Struct for storing the parameters of the scene being displayed
struct OgreSceneParameters{
	double value;
};

// Used to keep track of monitors information
struct MonitorInfo{
	Ogre::Vector3 pa;
	Ogre::Vector3 pb;
	Ogre::Vector3 pc;
};

// Storage of the OGRE scene configuration
extern OgreSceneParameters g_ogreSceneParams;

// Global variable used to signal when the Ogre3D window should close
extern bool g_kill3D;

// Global variable used to indicate when the Ogre3D engine is running
extern bool g_readyFor3D;

// Mutex to manage access to 3D graphics variables
extern HANDLE g_ogreMutex;

// Handle to manage the graphics thread
extern HANDLE g_graphicsThread;

// High-level thread management for graphics operations
void StartGraphicsThread();
void StopGraphicsThread();

// Thread used to handle graphics operations
DWORD WINAPI GraphicsThread(LPVOID lpParam);

class OgreApplication
{
public:
    OgreApplication(void);
    virtual ~OgreApplication(void);

    virtual void go(void);
	virtual void renderOneFrame(void);

    virtual bool setup();
    virtual bool configure(void);
	virtual bool createWindows();
	virtual void createScene();
    virtual void chooseSceneManager(void);
    virtual void createCameras(void);
    virtual void createViewports(void);
    virtual void setupResources(void);
    virtual void loadResources(void);
	
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
	MonitorInfo mMonitors[DISPLAY_COUNT];

	// Scene-specific
	Ogre::SceneNode* mPanelNodes[PANEL_COUNT];

    // Added for Mac compatibility
    Ogre::String m_ResourcePath;
};