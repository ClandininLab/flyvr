/*
Modified from tutorial Framework for Ogre 1.9 (http://www.ogre3d.org/wiki/)
*/

#include "stdafx.h"

#include "OgreApplication.h"
#include "mutex.h"

#define _USE_MATH_DEFINES
#include <math.h>

// Global variable instantiations
Pose3D g_realPose = { 0, 0, 0, 0, 0, 0 };
Pose3D g_virtualPose = { 0, 0, 0, 0, 0, 0 };
OgreSceneParameters g_ogreSceneParams;
bool g_kill3D = false;
bool g_readyFor3D = false;
HANDLE g_ogreMutex;
HANDLE g_graphicsThread;

// High-level management of the graphics thread
void StartGraphicsThread(){
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
		int iter = 0;

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

			// Print the framerate.
			if (iter % 1000 == 0){
				System::Console::WriteLine("FPS: {0:0.000}, {1:0.000}, {2:0.000}", 
					app.mWindows[0]->getLastFPS(), app.mWindows[1]->getLastFPS(), app.mWindows[2]->getLastFPS());
			}

			// Render the frame
			app.renderOneFrame();

			iter++;
		}
	}
	catch (Ogre::Exception& e) {
		std::cerr << "An exception has occured: " <<
			e.getFullDescription().c_str() << std::endl;
	}

	return TRUE;
}

OgreApplication::OgreApplication(void)
    : mRoot(0),
    mSceneMgr(0),
    mResourcesCfg(Ogre::StringUtil::BLANK),
    mPluginsCfg(Ogre::StringUtil::BLANK),
    mOverlaySystem(0)
{
    m_ResourcePath = "";
}

OgreApplication::~OgreApplication(void)
{
    delete mRoot;
}

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

void OgreApplication::chooseSceneManager(void)
{
    // Get the SceneManager, in this case a generic one
    mSceneMgr = mRoot->createSceneManager(Ogre::ST_GENERIC);

    // Initialize the OverlaySystem (changed for Ogre 1.9)
    mOverlaySystem = new Ogre::OverlaySystem();
    mSceneMgr->addRenderQueueListener(mOverlaySystem);
}

void OgreApplication::setCameraPosition(double x, double y, double z, unsigned idx)
{
	mCameras[idx]->setPosition(Ogre::Vector3(x, y, z));
}

void OgreApplication::setCameraTarget(double x, double y, double z, unsigned idx)
{
	mCameras[idx]->lookAt(Ogre::Vector3(x, y, z));
}

void OgreApplication::renderOneFrame(void)
{
	mRoot->renderOneFrame();
}

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

void OgreApplication::loadResources(void)
{
    Ogre::ResourceGroupManager::getSingleton().initialiseAllResourceGroups();
}

void OgreApplication::go(void)
{
    mResourcesCfg = m_ResourcePath + "resources.cfg";
    mPluginsCfg = m_ResourcePath + "plugins.cfg";

	setup();
}

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

    // Load resources
    loadResources();

    // Create the scene
    createScene();

    return true;
};

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