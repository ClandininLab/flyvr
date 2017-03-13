#include "stdafx.h"

/*
-----------------------------------------------------------------------------
Filename:    OgreApplication.cpp
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

#include "OgreApplication.h"

//---------------------------------------------------------------------------
OgreApplication::OgreApplication(void)
    : mRoot(0),
    mSceneMgr(0),
    mResourcesCfg(Ogre::StringUtil::BLANK),
    mPluginsCfg(Ogre::StringUtil::BLANK),
    mTrayMgr(0),
    mDetailsPanel(0),
    mCursorWasVisible(false),
    mInputManager(0),
    mMouse(0),
    mKeyboard(0),
    mOverlaySystem(0)
{
    m_ResourcePath = "";
}

//---------------------------------------------------------------------------
OgreApplication::~OgreApplication(void)
{
    if (mTrayMgr) delete mTrayMgr;
    if (mOverlaySystem) delete mOverlaySystem;

    // Remove ourself as a Window listener
    Ogre::WindowEventUtilities::removeWindowEventListener(mWindows[0], this);

    windowClosed(mWindows[0]);

    delete mRoot;
}

//---------------------------------------------------------------------------
bool OgreApplication::configure(void)
{
    // Show the configuration dialog and initialise the system.
    // You can skip this and use root.restoreConfig() to load configuration
    // settings if you were sure there are valid ones saved in ogre.cfg.
    if(mRoot->showConfigDialog())
    {
        // If returned true, user clicked OK so initialise.

        // Create multiple render windows, using code from PlayPen.cpp
		createWindows();

        return true;
    }
    else
    {
        return false;
    }
}
//---------------------------------------------------------------------------
bool OgreApplication::createWindows()
{
	// Create a render window on the first display
	Ogre::String strWindowName = "Window" + Ogre::StringConverter::toString(FIRST_DISPLAY);
	mWindows[0] = mRoot->initialise(true, strWindowName);

	// Create the rest of the windows.
	for (unsigned i = FIRST_DISPLAY+1; i <= (FIRST_DISPLAY+DISPLAY_COUNT-1); i++)
	{
		Ogre::String strWindowName = "Window" + Ogre::StringConverter::toString(i);

		// Select the desired monitor for this render window
		Ogre::NameValuePairList nvList;
		nvList["monitorIndex"] = Ogre::StringConverter::toString(i);

		// Create the render window, copying the width, height, and full screen setting from the
		// first monitor
		mWindows[i-FIRST_DISPLAY] = mRoot->createRenderWindow(strWindowName,
			mWindows[0]->getWidth(), mWindows[0]->getHeight(), mWindows[0]->isFullScreen(), &nvList);
		mWindows[i-FIRST_DISPLAY]->setDeactivateOnFocusChange(false);
	}

	return true;
}
//---------------------------------------------------------------------------
void OgreApplication::chooseSceneManager(void)
{
    // Get the SceneManager, in this case a generic one
    mSceneMgr = mRoot->createSceneManager(Ogre::ST_GENERIC);

    // Initialize the OverlaySystem (changed for Ogre 1.9)
    mOverlaySystem = new Ogre::OverlaySystem();
    mSceneMgr->addRenderQueueListener(mOverlaySystem);
}
//---------------------------------------------------------------------------
void OgreApplication::setCameraPosition(double x, double y, double z, unsigned idx)
{
	mCameras[idx]->setPosition(Ogre::Vector3(x, y, z));
}
//---------------------------------------------------------------------------
void OgreApplication::setCameraTarget(double x, double y, double z, unsigned idx)
{
	mCameras[idx-1]->lookAt(Ogre::Vector3(x, y, z));
}
//---------------------------------------------------------------------------
void OgreApplication::renderOneFrame(void)
{
	mRoot->renderOneFrame();
}
//---------------------------------------------------------------------------
void OgreApplication::createCameras(void)
{
	// Create the other cameras
	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
		Ogre::String strCameraName = "Camera" + Ogre::StringConverter::toString(i);
		mCameras[i] = mSceneMgr->createCamera(strCameraName);
		mCameras[i]->setPosition(Ogre::Vector3(0, 0, 80));
		mCameras[i]->lookAt(Ogre::Vector3(0, 0, -300));
	}
}
//---------------------------------------------------------------------------
void OgreApplication::createFrameListener(void)
{
    Ogre::LogManager::getSingletonPtr()->logMessage("*** Initializing OIS ***");
    OIS::ParamList pl;
    size_t windowHnd = 0;
    std::ostringstream windowHndStr;

    mWindows[0]->getCustomAttribute("WINDOW", &windowHnd);
    windowHndStr << windowHnd;
    pl.insert(std::make_pair(std::string("WINDOW"), windowHndStr.str()));

    mInputManager = OIS::InputManager::createInputSystem(pl);

    mKeyboard = static_cast<OIS::Keyboard*>(mInputManager->createInputObject(OIS::OISKeyboard, true));
    mMouse = static_cast<OIS::Mouse*>(mInputManager->createInputObject(OIS::OISMouse, true));

    mMouse->setEventCallback(this);
    mKeyboard->setEventCallback(this);

    // Set initial mouse clipping size
    windowResized(mWindows[0]);

    // Register as a Window listener
    Ogre::WindowEventUtilities::addWindowEventListener(mWindows[0], this);

    mInputContext.mKeyboard = mKeyboard;
    mInputContext.mMouse = mMouse;
    mTrayMgr = new OgreBites::SdkTrayManager("InterfaceName", mWindows[0], mInputContext, this);
    mTrayMgr->showFrameStats(OgreBites::TL_BOTTOMLEFT);

    mRoot->addFrameListener(this);
}
//---------------------------------------------------------------------------
void OgreApplication::destroyScene(void)
{
}
//---------------------------------------------------------------------------
void OgreApplication::createViewports(void)
{
	// Create camera for the secondary render windows.
	for (unsigned int i = 0; i < DISPLAY_COUNT; i++)
	{
		// Attach the camera
		Ogre::RenderWindow* pCurWindow = mWindows[i];
		Ogre::Viewport* vp = pCurWindow->addViewport(mCameras[i]);
		
		// Configure the viewport
		vp->setBackgroundColour(Ogre::ColourValue(0, 0, 0));
		mCameras[i]->setAspectRatio(Ogre::Real(vp->getActualWidth()) / Ogre::Real(vp->getActualHeight()));
	}
}
//---------------------------------------------------------------------------
void OgreApplication::setupResources(void)
{
    // Load resource paths from config file
    Ogre::ConfigFile cf;
    cf.load(mResourcesCfg);

    // Go through all sections & settings in the file
    Ogre::ConfigFile::SectionIterator seci = cf.getSectionIterator();

    Ogre::String secName, typeName, archName;
    while (seci.hasMoreElements())
    {
        secName = seci.peekNextKey();
        Ogre::ConfigFile::SettingsMultiMap *settings = seci.getNext();
        Ogre::ConfigFile::SettingsMultiMap::iterator i;
        for (i = settings->begin(); i != settings->end(); ++i)
        {
            typeName = i->first;
            archName = i->second;

#if OGRE_PLATFORM == OGRE_PLATFORM_APPLE
            // OS X does not set the working directory relative to the app.
            // In order to make things portable on OS X we need to provide
            // the loading with it's own bundle path location.
            if (!Ogre::StringUtil::startsWith(archName, "/", false)) // only adjust relative directories
                archName = Ogre::String(Ogre::macBundlePath() + "/" + archName);
#endif

            Ogre::ResourceGroupManager::getSingleton().addResourceLocation(
                archName, typeName, secName);
        }
    }
}
//---------------------------------------------------------------------------
void OgreApplication::createResourceListener(void)
{
}
//---------------------------------------------------------------------------
void OgreApplication::loadResources(void)
{
    Ogre::ResourceGroupManager::getSingleton().initialiseAllResourceGroups();
}
//---------------------------------------------------------------------------
void OgreApplication::go(void)
{
#ifdef _DEBUG
#ifndef OGRE_STATIC_LIB
    mResourcesCfg = m_ResourcePath + "resources_d.cfg";
    mPluginsCfg = m_ResourcePath + "plugins_d.cfg";
#else
    mResourcesCfg = "resources_d.cfg";
    mPluginsCfg = "plugins_d.cfg";
#endif
#else
#ifndef OGRE_STATIC_LIB
    mResourcesCfg = m_ResourcePath + "resources.cfg";
    mPluginsCfg = m_ResourcePath + "plugins.cfg";
#else
    mResourcesCfg = "resources.cfg";
    mPluginsCfg = "plugins.cfg";
#endif
#endif

	setup();

}
//---------------------------------------------------------------------------
bool OgreApplication::setup(void)
{
    mRoot = new Ogre::Root(mPluginsCfg);

    setupResources();

    bool carryOn = configure();
    if (!carryOn) return false;

    chooseSceneManager();
    createCameras();
    createViewports();

    // Set default mipmap level (NB some APIs ignore this)
    Ogre::TextureManager::getSingleton().setDefaultNumMipmaps(5);

    // Create any resource listeners (for loading screens)
    createResourceListener();
    // Load resources
    loadResources();

    // Create the scene
    createScene();

    createFrameListener();

    return true;
};
//---------------------------------------------------------------------------
bool OgreApplication::frameRenderingQueued(const Ogre::FrameEvent& evt)
{
    if(mWindows[0]->isClosed())
        return false;

    // Need to capture/update each device
    mKeyboard->capture();
    mMouse->capture();

    mTrayMgr->frameRenderingQueued(evt);

    return true;
}
//---------------------------------------------------------------------------
bool OgreApplication::keyPressed( const OIS::KeyEvent &arg )
{
    return true;
}
//---------------------------------------------------------------------------
bool OgreApplication::keyReleased(const OIS::KeyEvent &arg)
{
    return true;
}
//---------------------------------------------------------------------------
bool OgreApplication::mouseMoved(const OIS::MouseEvent &arg)
{
    return true;
}
//---------------------------------------------------------------------------
bool OgreApplication::mousePressed(const OIS::MouseEvent &arg, OIS::MouseButtonID id)
{
    return true;
}
//---------------------------------------------------------------------------
bool OgreApplication::mouseReleased(const OIS::MouseEvent &arg, OIS::MouseButtonID id)
{
    return true;
}
//---------------------------------------------------------------------------
// Adjust mouse clipping area
void OgreApplication::windowResized(Ogre::RenderWindow* rw)
{
    unsigned int width, height, depth;
    int left, top;
    rw->getMetrics(width, height, depth, left, top);

    const OIS::MouseState &ms = mMouse->getMouseState();
    ms.width = width;
    ms.height = height;
}
//---------------------------------------------------------------------------
// Unattach OIS before window shutdown (very important under Linux)
void OgreApplication::windowClosed(Ogre::RenderWindow* rw)
{
    // Only close for window that created OIS (the main window in these demos)
    if(rw == mWindows[0])
    {
        if(mInputManager)
        {
            mInputManager->destroyInputObject(mMouse);
            mInputManager->destroyInputObject(mKeyboard);

            OIS::InputManager::destroyInputSystem(mInputManager);
            mInputManager = 0;
        }
    }
}

void OgreApplication::createScene(void)
{
	mSceneMgr->setAmbientLight(Ogre::ColourValue(0.5, 0.5, 0.5));

	// Set the position of all cameras
	setCameraPosition(0, 47, 222, 0);
	setCameraPosition(0, 47, 222, 1);
	setCameraPosition(0, 47, 222, 2);

	Ogre::Light* light = mSceneMgr->createLight("MainLight");
	light->setPosition(20.0, 80.0, 50.0);

	Ogre::Entity* ogreEntity = mSceneMgr->createEntity("ogrehead.mesh");

	Ogre::SceneNode* ogreNode = mSceneMgr->getRootSceneNode()->createChildSceneNode();
	ogreNode->attachObject(ogreEntity);

	Ogre::Entity* ogreEntity2 = mSceneMgr->createEntity("ogrehead.mesh");

	Ogre::SceneNode* ogreNode2 = mSceneMgr->getRootSceneNode()->createChildSceneNode(
		Ogre::Vector3(84, 48, 0));
	ogreNode2->attachObject(ogreEntity2);

	Ogre::Entity* ogreEntity3 = mSceneMgr->createEntity("ogrehead.mesh");

	Ogre::SceneNode* ogreNode3 = mSceneMgr->getRootSceneNode()->createChildSceneNode();
	ogreNode3->setPosition(Ogre::Vector3(0, 104, 0));
	ogreNode3->setScale(Ogre::Real(2), Ogre::Real(1.2), Ogre::Real(1));
	ogreNode3->attachObject(ogreEntity3);

	Ogre::Entity* ogreEntity4 = mSceneMgr->createEntity("ogrehead.mesh");

	Ogre::SceneNode* ogreNode4 = mSceneMgr->getRootSceneNode()->createChildSceneNode();
	ogreNode4->setPosition(-84, 48, 0);
	ogreNode4->roll(Ogre::Degree(-90));
	ogreNode4->attachObject(ogreEntity4);

}

#if OGRE_PLATFORM == OGRE_PLATFORM_WIN32
#define WIN32_LEAN_AND_MEAN
#include "windows.h"
#endif

//---------------------------------------------------------------------------