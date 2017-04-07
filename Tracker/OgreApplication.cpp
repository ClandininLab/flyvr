// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

// OgreApplication is based on the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#include <chrono>
#include <SimpleIni.h>

#include "OgreApplication.h"
#include "StimManager.h"
#include "mutex.h"

#define _USE_MATH_DEFINES
#include <math.h>

using namespace std::chrono;

// Global variable instantiations
bool g_kill3D = false;
bool g_readyFor3D = false;
HANDLE g_ogreMutex;
HANDLE g_graphicsThread;

// Initialize poses
Pose3D g_realPose = { 0, 0, 0, 0, 0, 0 };
Pose3D g_virtPose = { 0, 0, 0, 0, 0, 0 };

// High-level management of the graphics thread
void StartGraphicsThread(void){
	// Graphics setup
	g_ogreMutex = CreateMutex(NULL, FALSE, NULL);
	DWORD gfxThreadID;
	g_graphicsThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)GraphicsThread, NULL, 0, &gfxThreadID);

	// Wait for 3D engine to be up and running
	while (!g_readyFor3D);
}

void StopGraphicsThread(void){
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
		StimManager stim(app);

		g_readyFor3D = true;

		while (!g_kill3D){
			// Record iteration start time
			auto loopStart = high_resolution_clock::now();

			// Read out real pose and virtual pose
			Pose3D realPose, virtPose;
			LOCK(g_ogreMutex);
			realPose = g_realPose;
			virtPose = g_virtPose;
			UNLOCK(g_ogreMutex);

			// Update the stimulus
			stim.Update();

			// Create the top node
			Ogre::SceneNode *rootNode = app.mSceneMgr->getRootSceneNode();

			// Move scene based on difference between real position and virtual position
			Ogre::Vector3 realPosition = Ogre::Vector3(realPose.x, realPose.y, realPose.z);
			Ogre::Vector3 virtPosition = Ogre::Vector3(virtPose.x, virtPose.y, virtPose.z);
			rootNode->setPosition(realPosition - virtPosition);

			// Rotate scene based on difference between real orientation and virtual orientation
			rootNode->setOrientation(rootNode->getInitialOrientation());
			rootNode->pitch(Ogre::Radian(realPose.pitch - virtPose.pitch));
			rootNode->yaw(Ogre::Radian(realPose.yaw - virtPose.yaw));
			rootNode->roll(Ogre::Radian(realPose.roll - virtPose.roll));

			// Update the projection matrices based on eye position
			app.updateProjMatrices(realPosition);

			// Render the frame
			app.renderOneFrame();

			// Record iteration stop time
			auto loopStop = high_resolution_clock::now();

			// Aim for a target frame rate
			auto loopDuration = duration<double>(loopStop - loopStart).count();
			if (loopDuration >= TARGET_FRAME_DURATION){
				std::cout << "Slow frame (" << loopDuration << " s)\n";
			}
			else {
				Sleep(round(1000 * (TARGET_FRAME_DURATION - loopDuration)));
			}
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
    m_ResourcePath = "C:\\dev\\Tracker\\x64\\Release\\";
}

OgreApplication::~OgreApplication(void)
{
    delete mRoot;
}

void OgreApplication::configure(void)
{
    // Show the configuration dialog and initialise the system.
    // You can skip this and use root.restoreConfig() to load configuration
    // settings if you were sure there are valid ones saved in ogre.cfg.
    if(mRoot->restoreConfig())
    {
       // Create multiple render windows
		createWindows();
    }
    else
    {
		throw std::exception("Could not restore Ogre3D config.");
    }
}

bool OgreApplication::createWindows(void)
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

void OgreApplication::defineMonitors(void){
	// Width and height of each monitor
	double W = DISPLAY_WIDTH_METERS;
	double H = DISPLAY_HEIGHT_METERS;

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
}

void OgreApplication::createCameras(void)
{
	// Define the monitor geometry
	defineMonitors();

	// Create all cameras
	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
		Ogre::String strCameraName = "Camera" + Ogre::StringConverter::toString(i);
		mCameras[i] = mSceneMgr->createCamera(strCameraName);
	}

	// Update the projection matrices assuming the eye is at the origin
	Ogre::Vector3 pe = Ogre::Vector3(0, 0, 0);
	updateProjMatrices(pe);
}

void OgreApplication::updateProjMatrices(const Ogre::Vector3 &pe){
	// Update project matrix used for each display
	// Reference: http://csc.lsu.edu/~kooima/articles/genperspective/

	for (unsigned i = 0; i < DISPLAY_COUNT; i++){
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
		Ogre::Real n = Ogre::Real(NEAR_CLIP_DIST);
		Ogre::Real f = Ogre::Real(FAR_CLIP_DIST);

		// Compute screen coordinates
		Ogre::Real l = vr.dotProduct(va)*n / d;
		Ogre::Real r = vr.dotProduct(vb)*n / d;
		Ogre::Real b = vu.dotProduct(va)*n / d;
		Ogre::Real t = vu.dotProduct(vc)*n / d;

		// Create the composite projection matrix

		// Original projection matrix
		Ogre::Matrix4 P = Ogre::Matrix4(
			(2.0*n)/(r-l),             0,    (r+l)/(r-l),                0,
			            0, (2.0*n)/(t-b),    (t+b)/(t-b),                0,
			            0,             0,   -(f+n)/(f-n), -(2.0*f*n)/(f-n),
			            0,             0,             -1,                0);

		// Rotation matrix
		Ogre::Matrix4 M = Ogre::Matrix4(
			vr.x, vu.x, vn.x,    0,
			vr.y, vu.y, vn.y,    0,
			vr.z, vu.z, vn.z,    0,
			   0,    0,    0,    1);

		// Translation matrix
		Ogre::Matrix4 T = Ogre::Matrix4(
			   1,    0,    0, -pe.x,
			   0,    1,    0, -pe.y,
			   0,    0,    1, -pe.z,
			   0,    0,    0,     1);

		Ogre::Matrix4 offAxis = P*M.transpose()*T;

		mCameras[i]->setCustomProjectionMatrix(true, offAxis);
	}
}

void OgreApplication::createViewports(void)
{
	// Attach each camera to each respective window
	for (unsigned int i = 0; i < DISPLAY_COUNT; i++){
		mViewports[i] = mWindows[i]->addViewport(mCameras[i]);
	}
}

void OgreApplication::setBackground(double r, double g, double b){
	// Configure the viewport
	for (unsigned int i = 0; i < DISPLAY_COUNT; i++){
		mViewports[i]->setBackgroundColour(Ogre::ColourValue(r, g, b));
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

    configure();

    chooseSceneManager();
    createCameras();
    createViewports();

    // Set default mipmap level (NB some APIs ignore this)
    Ogre::TextureManager::getSingleton().setDefaultNumMipmaps(5);

    // Load resources
    loadResources();

    return true;
};