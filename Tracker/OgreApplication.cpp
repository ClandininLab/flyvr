/*
Modified from tutorial Framework for Ogre 1.9 (http://www.ogre3d.org/wiki/)
*/

#include "stdafx.h"

#include "OgreApplication.h"
#include "mutex.h"

#define _USE_MATH_DEFINES
#include <math.h>

// Global variable instantiations
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

	try {
		app.go();

		g_readyFor3D = true;
		int iter = 0;

		while (!g_kill3D){
			// Update displays
			//for (unsigned i = 0; i < DISPLAY_COUNT; i++){
			//}

			double val;
			LOCK(g_ogreMutex);
			val = g_ogreSceneParams.value;
			UNLOCK(g_ogreMutex);

			double W = DISPLAY_WIDTH_METERS;
			double H = DISPLAY_HEIGHT_METERS;

			double R = W / 2.0 + 1;

			double x = -R*cos(M_PI*val);
			double y = 0;
			double z = -R*sin(M_PI*val);
			double angle = M_PI / 2 - M_PI*val;
			Ogre::Vector3 newPos = Ogre::Vector3(x, y, z);
			app.mPanelNodes[0]->setPosition(newPos);
			//app.mPanelNodes[0]->setOrientation(app.mPanelNodes[0]->getInitialOrientation());
			//app.mPanelNodes[0]->yaw(Ogre::Radian(angle));

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

void OgreApplication::renderOneFrame(void)
{
	mRoot->renderOneFrame();
}

void OgreApplication::createCameras(void)
{
	// Width and height of each monitor
	double W = DISPLAY_WIDTH_METERS;
	double H = DISPLAY_HEIGHT_METERS;

	// Define eye position
	Ogre::Vector3 pe = Ogre::Vector3(0, 0, 0);

	// North monitor
	mMonitors[NORTH].pa = Ogre::Vector3(-W / 2., -H / 2., -W / 2.);
	mMonitors[NORTH].pb = mMonitors[NORTH].pa + Ogre::Vector3(W, 0, 0);
	mMonitors[NORTH].pc = mMonitors[NORTH].pa + Ogre::Vector3(0, H, 0);

	// West monitor
	mMonitors[WEST].pa = Ogre::Vector3(-W / 2., -H / 2., W / 2.);
	mMonitors[WEST].pb = mMonitors[WEST].pa + Ogre::Vector3(0, 0, -W);
	mMonitors[WEST].pc = mMonitors[WEST].pa + Ogre::Vector3(0, H, 0);
	
	// East monitor
	mMonitors[EAST].pa = Ogre::Vector3(W / 2., -H / 2., -W / 2.);
	mMonitors[EAST].pb = mMonitors[EAST].pa + Ogre::Vector3(0, 0, W);
	mMonitors[EAST].pc = mMonitors[EAST].pa + Ogre::Vector3(0, H, 0);

	// Create the other cameras
	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
		Ogre::String strCameraName = "Camera" + Ogre::StringConverter::toString(i);
		mCameras[i] = mSceneMgr->createCamera(strCameraName);

		// Determine monitor coordinates
		Ogre::Vector3 pa = mMonitors[i].pa;
		Ogre::Vector3 pb = mMonitors[i].pb;
		Ogre::Vector3 pc = mMonitors[i].pc;

		// Determine monitor unit vectors
		Ogre::Vector3 vr = pb - pa;
		vr.normalise();
		Ogre::Vector3 vu = pc - pa;
		vu.normalise();
		Ogre::Vector3 vn = vr.crossProduct(vu);
		vn.normalise();

		// Determine frustum extents
		Ogre::Vector3 va = pa - pe;
		Ogre::Vector3 vb = pb - pe;
		Ogre::Vector3 vc = pc - pe;

		// Compute distance to screen
		Ogre::Real d = -vn.dotProduct(va);

		// Set clipping distance to screen distance
		// May want to revist this later
		Ogre::Real n = d;

		// Compute screen coordinates
		Ogre::Real l = vr.dotProduct(va)*n / d;
		Ogre::Real r = vr.dotProduct(vb)*n / d;
		Ogre::Real b = vu.dotProduct(va)*n / d;
		Ogre::Real t = vu.dotProduct(vc)*n / d;

		// Define far clipping distance to be 10 meters
		// May want to revisit this later
		double f = 10.0;

		// Create projection matrix
		Ogre::Matrix4 P, M, T;

		P = Ogre::Matrix4(
			(2.0f*n) / (r - l), 0, ((r + l) / (r - l)), 0,
			0, ((2.0f*n) / (t - b)), ((t + b) / (t - b)), 0,
			0, 0, -(f + n) / (f - n), -(2.0f*f*n) / (f - n),
			0, 0, -1, 0);

		M = Ogre::Matrix4(
			vr.x, vu.x, vn.x,    0,
			vr.y, vu.y, vn.y,    0,
			vr.z, vu.z, vn.z,    0,
			   0,    0,    0,    1);

		T = Ogre::Matrix4(
			   1,    0,    0,   -pe.x,
			   0,    1,    0,   -pe.y,
			   0,    0,    1,   -pe.z,
			   0,    0,    0,       1);

		Ogre::Matrix4 offAxis = P*M.transpose()*T;

		mCameras[i]->setCustomProjectionMatrix(true, offAxis);
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

void OgreApplication::createScene(void)
{	
	mSceneMgr->setAmbientLight(Ogre::ColourValue(0.5, 0.5, 0.5));

	Ogre::Light* light = mSceneMgr->createLight("MainLight");
	light->setPosition(0.0, 2*DISPLAY_HEIGHT_METERS, 0);

	Ogre::Entity* panelEnt = mSceneMgr->createEntity("cube.mesh");
	mPanelNodes[0] = mSceneMgr->getRootSceneNode()->createChildSceneNode();

	double normal = 0.01;
	double side = 0.5;
	mPanelNodes[0]->setScale(
		Ogre::Real(normal * side),
		Ogre::Real(normal * side),
		Ogre::Real(normal * side));
	mPanelNodes[0]->setPosition(Ogre::Vector3(-DISPLAY_WIDTH_METERS*2, 0.0, -DISPLAY_WIDTH_METERS/2.0-side));

	mPanelNodes[0]->attachObject(panelEnt);
}