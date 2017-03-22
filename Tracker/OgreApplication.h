// Steven Herbst
// sherbst@stanford.edu

// Modified from the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#ifndef OGRE_APPLICATION_H
#define OGRE_APPLICATION_H

#include <OgreCamera.h>
#include <OgreEntity.h>
#include <OgreLogManager.h>
#include <OgreRoot.h>
#include <OgreViewport.h>
#include <OgreSceneManager.h>
#include <OgreRenderWindow.h>
#include <OgreConfigFile.h>

#include <OISEvents.h>
#include <OISInputManager.h>
#include <OISKeyboard.h>
#include <OISMouse.h>

#include <SdkTrays.h>

#define DISPLAY_COUNT 3
#define DISPLAY_LIST  {1,2,3}

#define PATTERN_RADIUS 222
#define PANEL_THICKNESS 1
#define PANEL_HEIGHT 200
#define PANEL_COUNT 100

#define WEST  1
#define NORTH 0
#define EAST  2

#define DISPLAY_WIDTH_METERS 1.111
#define DISPLAY_HEIGHT_METERS 0.623

#define DISPLAY_WIDTH_PIXELS 1600
#define DISPLAY_HEIGHT_PIXELS 900
#define DISPLAY_FULLSCREEN true

// Struct for storing the parameters of the scene being displayed
struct OgreSceneParameters{
	double rotation;
};

// Struct for communicating 3D coordinate information
// to OGRE through threads.
struct Pose3D{
	double x;
	double y;
	double z;
	double roll;
	double pitch;
	double yaw;
};

// Storage of the camera position and look direction for each display
Pose3D g_realPose = { 0, 0, 0, 0, 0, 0 };
Pose3D g_virtualPose = { 0, 0, 0, 0, 0, 0 };

// Storage of the OGRE scene configuration
OgreSceneParameters g_ogreSceneParams;

// Global variable used to signal when the Ogre3D window should close
bool g_kill3D = false;

// Global variable used to indicate when the Ogre3D engine is running
bool g_readyFor3D = false;

// Mutex to manage access to 3D graphics variables
HANDLE g_ogreMutex;

// Handle to manage the graphics thread
HANDLE g_graphicsThread;

// High-level thread management for graphics operations
void StartGraphicsThread();
void StopGraphicsThread();

// Thread used to handle graphics operations
DWORD WINAPI GraphicsThread(LPVOID lpParam);

class OgreApplication : public Ogre::FrameListener, public Ogre::WindowEventListener, public OIS::KeyListener, public OIS::MouseListener, OgreBites::SdkTrayListener
{
public:
    OgreApplication(void);
    virtual ~OgreApplication(void);

    virtual void go(void);
	virtual void setCameraPosition(double x, double y, double z, unsigned idx);
	virtual void setCameraTarget(double x, double y, double z, unsigned idx);
	virtual void setPatternRotation(double rad);
	virtual void renderOneFrame(void);
	virtual void destroyScene(void);

protected:
    virtual bool setup();
    virtual bool configure(void);
	virtual bool createWindows();
	virtual void createScene();
    virtual void chooseSceneManager(void);
    virtual void createCameras(void);
    virtual void createFrameListener(void);
    virtual void createViewports(void);
    virtual void setupResources(void);
    virtual void createResourceListener(void);
    virtual void loadResources(void);
    virtual bool frameRenderingQueued(const Ogre::FrameEvent& evt);

    virtual bool keyPressed(const OIS::KeyEvent &arg);
    virtual bool keyReleased(const OIS::KeyEvent &arg);
    virtual bool mouseMoved(const OIS::MouseEvent &arg);
    virtual bool mousePressed(const OIS::MouseEvent &arg, OIS::MouseButtonID id);
    virtual bool mouseReleased(const OIS::MouseEvent &arg, OIS::MouseButtonID id);

    // Adjust mouse clipping area
    virtual void windowResized(Ogre::RenderWindow* rw);
    // Unattach OIS before window shutdown (very important under Linux)
    virtual void windowClosed(Ogre::RenderWindow* rw);
	
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

	// Scene-specific
	Ogre::SceneNode* mPanelNodes[PANEL_COUNT];

    // OgreBites
    OgreBites::InputContext mInputContext;
    OgreBites::SdkTrayManager* mTrayMgr;
    OgreBites::ParamsPanel* mDetailsPanel; // Sample details panel
    bool mCursorWasVisible;	// Was cursor visible before dialog appeared?

    //OIS Input devices
    OIS::InputManager* mInputManager;
    OIS::Mouse* mMouse;
    OIS::Keyboard* mKeyboard;

    // Added for Mac compatibility
    Ogre::String m_ResourcePath;
};

#endif

