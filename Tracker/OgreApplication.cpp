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
#include "mutex.h"

#define _USE_MATH_DEFINES
#include <math.h>

// High-level management of the graphics thread
void StartGraphicsThread(){
	// Read in stimulus configuration

	// Graphics setup
	g_ogreMutex = CreateMutex(NULL, FALSE, NULL);
	DWORD gfxThreadID;
	g_graphicsThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)GraphicsThread, NULL, 0, &gfxThreadID);

	// Wait for 3D engine to be up and running
	while (!g_readyFor3D);
}

void StopGraphicsThread(){
	// Kill the 3D graphics thread
	g_kill3D = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(g_graphicsThread, INFINITE);

	// Close the handles to the mutexes and graphics thread
	CloseHandle(g_graphicsThread);
	CloseHandle(g_ogreMutex);
}

// Thread used to handle graphics operations
DWORD WINAPI GraphicsThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);

	OgreApplication app;
	Pose3D realPose, virtualPose;

	try {
		app.go();
		g_readyFor3D = true;

		while (!g_kill3D){
			// Copy over the camera position information
			LOCK(g_ogreMutex);
				realPose = g_realPose;
				virtualPose = g_virtualPose;
			UNLOCK(g_ogreMutex);

			// Reposition the cameras
			for (unsigned i = 0; i < DISPLAY_COUNT; i++){
				// TODO: update each screen given realPose and virtualPose
			}

			// Render the frame
			app.renderOneFrame();
		}
	}
	catch (Ogre::Exception& e) {
		std::cerr << "An exception has occured: " <<
			e.getFullDescription().c_str() << std::endl;
	}

	return TRUE;
}


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
    if(mRoot->restoreConfig())
    {
       // Create multiple render windows
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
	// Multiple window code modified from PlayPen.cpp

	// Initialize root, but do not create a render window yet
	mRoot->initialise(false);

	// Create array of monitor indices
	const unsigned monitorIndices[] = DISPLAY_LIST;

	// Create all render windows
	for (unsigned i = 0; i < DISPLAY_COUNT; i++)
	{
		unsigned monitorIndex = monitorIndices[i];

		Ogre::String strWindowName = "Window" + Ogre::StringConverter::toString(monitorIndex);

		// Select the desired monitor for this render window
		Ogre::NameValuePairList nvList;
		nvList["monitorIndex"] = Ogre::StringConverter::toString(monitorIndex);

		// Create the render window, copying the width, height, and full screen setting from the
		// first monitor
		mWindows[i] = mRoot->createRenderWindow(strWindowName,
			DISPLAY_WIDTH_PIXELS, DISPLAY_HEIGHT_PIXELS, DISPLAY_FULLSCREEN, &nvList);
		mWindows[i]->setDeactivateOnFocusChange(false);
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
	mCameras[idx]->lookAt(Ogre::Vector3(x, y, z));
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
		mCameras[i]->setNearClipDistance(Ogre::Real(DISPLAY_WIDTH_METERS / 2.0));
		mCameras[i]->setFOVy(Ogre::Radian(0.51238946));
		setCameraPosition(0.0, 0.0, 80.0, i);
		setCameraTarget(0.0, 0.0, -300.0, i);
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
    mResourcesCfg = m_ResourcePath + "resources.cfg";
    mPluginsCfg = m_ResourcePath + "plugins.cfg";

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

void OgreApplication::setPatternRotation(double rad){
	double delta = 2 * M_PI / double(PANEL_COUNT);

	for (unsigned i = 0; i < PANEL_COUNT; i += 2){
		double angle = i*delta + rad;
		mPanelNodes[i]->setPosition(Ogre::Vector3(PATTERN_RADIUS*cos(angle), 0.0, PATTERN_RADIUS*sin(angle)));
		mPanelNodes[i]->setOrientation(mPanelNodes[i]->getInitialOrientation());
		mPanelNodes[i]->yaw(Ogre::Radian(-M_PI / 2 - angle));
	}
}

void OgreApplication::createScene(void)
{
	mSceneMgr->setAmbientLight(Ogre::ColourValue(0.5, 0.5, 0.5));

	// Set the position of all cameras
	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
		setCameraPosition(0, 47, 222, i);
	}

	Ogre::Light* light = mSceneMgr->createLight("MainLight");
	light->setPosition(20.0, 80.0, 50.0);

	double delta = 2 * M_PI / double(PANEL_COUNT);
	double panel_width = 2 * PATTERN_RADIUS * tan(delta / 2.0);

	for (unsigned i = 0; i < PANEL_COUNT; i += 2){
		Ogre::Entity* panelEnt = mSceneMgr->createEntity("cube.mesh");
		mPanelNodes[i] = mSceneMgr->getRootSceneNode()->createChildSceneNode();

		double angle = i*delta;
		mPanelNodes[i]->setScale(Ogre::Real(0.01 * panel_width), 
			                     Ogre::Real(0.01 * PANEL_HEIGHT), 
						         Ogre::Real(0.01 * PANEL_THICKNESS));
		mPanelNodes[i]->attachObject(panelEnt);
	}

	setPatternRotation(0);
}
