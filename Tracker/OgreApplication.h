/*
-----------------------------------------------------------------------------
Filename:    OgreApplication.h
-----------------------------------------------------------------------------

This source file is part of the
   ___                 __    __ _ _    _
  /___\__ _ _ __ ___  / / /\ \ (_) | _(_)
 //  // _` | '__/ _ \ \ \/  \/ / | |/ / |
/ \_// (_| | | |  __/  \  /\  /| |   <| |
\___/ \__, |_|  \___|   \/  \/ |_|_|\_\_|
      |___/
Tutorial Framework (for Ogre 1.9)
http://www.ogre3d.org/wiki/
-----------------------------------------------------------------------------
*/

#ifndef __OgreApplication_h_
#define __OgreApplication_h_

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

//---------------------------------------------------------------------------

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

	Ogre::SceneNode*            mPanelNodes[PANEL_COUNT];

    Ogre::Root*                 mRoot;
	Ogre::Camera*               mCameras[DISPLAY_COUNT];
    Ogre::SceneManager*         mSceneMgr;
    Ogre::RenderWindow*         mWindows[DISPLAY_COUNT];
    Ogre::String                mResourcesCfg;
    Ogre::String                mPluginsCfg;

    Ogre::OverlaySystem*        mOverlaySystem;

    // OgreBites
    OgreBites::InputContext     mInputContext;
    OgreBites::SdkTrayManager*	mTrayMgr;
    OgreBites::ParamsPanel*     mDetailsPanel;   	// Sample details panel
    bool                        mCursorWasVisible;	// Was cursor visible before dialog appeared?

    //OIS Input devices
    OIS::InputManager*          mInputManager;
    OIS::Mouse*                 mMouse;
    OIS::Keyboard*              mKeyboard;

    // Added for Mac compatibility
    Ogre::String                 m_ResourcePath;
};

//---------------------------------------------------------------------------

#endif // #ifndef __OgreApplication_h_

//---------------------------------------------------------------------------