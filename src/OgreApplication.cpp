// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

// OgreApplication is based on the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#include <chrono>
#include <atomic>

#define _USE_MATH_DEFINES
#include <math.h>

#include <SimpleIni.h>

#include "OgreApplication.h"
#include "StimManager.h"
#include "Utility.h"

using namespace std::chrono;

namespace OgreApplicationNamespace{
	// Name of configuration file
	auto GraphicsConfigFile = "tv.ini";

	// Path to folder containing CFG files
	// TODO: determine this automatically
	auto ResourcePath = "";

	// Global variables used to manage access to real and virtual viewer position
	std::atomic<Pose3D> g_flyPose3D;

	// Variables used to manage graphics thread
	bool kill3D = false;
	std::thread graphicsThread;

	// Variables used to signal when the graphics thread has started up
	BoolSignal readyFor3D;
}

using namespace OgreApplicationNamespace;

// High-level management of the graphics thread
void StartGraphicsThread(void){
	std::cout << "Starting graphics thread.\n";

	// Graphics setup;
	graphicsThread = std::thread(GraphicsThread);

	// Wait for 3D engine to be up and running
	readyFor3D.wait();
}

void StopGraphicsThread(void){
	std::cout << "Stopping graphics thread.\n";

	// Kill the 3D graphics thread
	kill3D = true;

	// Wait for graphics thread to terminate
	graphicsThread.join();
}

void SetFlyPose3D(Pose3D flyPose3D){
	g_flyPose3D.store(flyPose3D);
}

// Thread used to handle graphics operations
void GraphicsThread(void){

	// Create OGRE application
	OgreApplication app;

	// Read in configuration information
	app.readGraphicsConfig(GraphicsConfigFile);

	// Launch application
	app.setup();

	// Attach application to stimulus manager
	StimManager stim(app);

	// Let the main thread know that the 3D application is up and running
	readyFor3D.update(true);

	// Timing manager for the loop
	TimeManager timeManager("GraphicsThread");
	timeManager.start();

	while (!kill3D){
		// Log start of loop
		timeManager.tick();

		// Read out real pose and virtual pose
		Pose3D flyPose3D = g_flyPose3D.load();

		// Update the stimulus
		stim.Update(flyPose3D);

		// Update the projection matrices based on eye position
		app.updateProjMatrices(flyPose3D.x, flyPose3D.y, flyPose3D.z);

		// Render the frame
		app.renderOneFrame();

		// Ensure a maximum framerate
		timeManager.waitUntil(app.targetLoopDuration);
	}
}

OgreApplication::OgreApplication(void)
	: mRoot(nullptr),
	mSceneMgr(nullptr),
	mOverlaySystem(nullptr)
{
}

OgreApplication::~OgreApplication(void)
{
	delete mRoot;
}

void OgreApplication::readGraphicsConfig(const char* loc){
	// Load the INI file
	CSimpleIniA iniFile;
	iniFile.SetUnicode();
	iniFile.LoadFile(loc);

	// Read global parameters
	mNearClipDist = iniFile.GetDoubleValue("", "near-clip-dist", 0.01);
	mFarClipDist = iniFile.GetDoubleValue("", "far-clip-dist", 10.0);

	// Read the target loop duration
	targetLoopDuration = iniFile.GetDoubleValue("", "target-loop-duration", 8e-3);

	// Read all section names
	CSimpleIniA::TNamesDepend sections;
	iniFile.GetAllSections(sections);

	// Iterate from section names
	for (auto iSection = sections.begin(); iSection != sections.end(); ++iSection) {
		std::string sectionName = std::string(iSection->pItem);
		if (sectionName != ""){
			MonitorInfo monitor;

			// Configuration information
			monitor.id = iniFile.GetLongValue(sectionName.c_str(), "id", 1);
			monitor.pixelWidth = iniFile.GetLongValue(sectionName.c_str(), "width-pixels", 1440);
			monitor.pixelHeight = iniFile.GetLongValue(sectionName.c_str(), "height-pixels", 900);
			monitor.displayFullscreen = iniFile.GetBoolValue(sectionName.c_str(), "display-fullscreen", true);

			// Read vector "pa"
			double pax = iniFile.GetDoubleValue(sectionName.c_str(), "pax", 0.0);
			double pay = iniFile.GetDoubleValue(sectionName.c_str(), "pay", 0.0);
			double paz = iniFile.GetDoubleValue(sectionName.c_str(), "paz", 0.0);
			monitor.pa = Ogre::Vector3(pax, pay, paz);

			// Read vector "pb"
			double pbx = iniFile.GetDoubleValue(sectionName.c_str(), "pbx", 0.0);
			double pby = iniFile.GetDoubleValue(sectionName.c_str(), "pby", 0.0);
			double pbz = iniFile.GetDoubleValue(sectionName.c_str(), "pbz", 0.0);
			monitor.pb = Ogre::Vector3(pbx, pby, pbz);

			// Read vector "pc"
			double pcx = iniFile.GetDoubleValue(sectionName.c_str(), "pcx", 0.0);
			double pcy = iniFile.GetDoubleValue(sectionName.c_str(), "pcy", 0.0);
			double pcz = iniFile.GetDoubleValue(sectionName.c_str(), "pcz", 0.0);
			monitor.pc = Ogre::Vector3(pcx, pcy, pcz);

			// Add monitor information to vector
			mMonitors.push_back(monitor);
		}
	}
}

void OgreApplication::createWindows(void)
{
	// Multiple window code modified from PlayPen.cpp

	// Initialize root, but do not create a render window yet
	mRoot->initialise(false);

	// Create all render windows
	for (auto monitor: mMonitors)
	{
		Ogre::String strWindowName = "Window" + Ogre::StringConverter::toString(monitor.id);

		// Select the desired monitor for this render window
		Ogre::NameValuePairList nvList;
		nvList["monitorIndex"] = Ogre::StringConverter::toString(monitor.id);

		// Create the new render window and set it up
		Ogre::RenderWindow *window = mRoot->createRenderWindow(strWindowName,
			monitor.pixelWidth, monitor.pixelHeight, monitor.displayFullscreen, &nvList);
		window->setDeactivateOnFocusChange(false);

		// Add to window list
		mWindows.push_back(window);
	}
}

void OgreApplication::renderOneFrame(void)
{
	mRoot->renderOneFrame();
}

void OgreApplication::updateProjMatrices(double x, double y, double z){
	// Update project matrix used for each display
	// Reference: http://csc.lsu.edu/~kooima/articles/genperspective/

	// Vector corresponding to eye position
	Ogre::Vector3 pe(x, y, z);

	// Update projection matrix for each display
	for (unsigned i = 0; i < mMonitors.size(); i++){
		MonitorInfo monitor = mMonitors[i];

		// Determine monitor coordinates
		Ogre::Vector3 pa = monitor.pa;
		Ogre::Vector3 pb = monitor.pb;
		Ogre::Vector3 pc = monitor.pc;

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
		Ogre::Real n = Ogre::Real(mNearClipDist);
		Ogre::Real f = Ogre::Real(mFarClipDist);

		// Compute screen coordinates
		Ogre::Real l = vr.dotProduct(va)*n / d;
		Ogre::Real r = vr.dotProduct(vb)*n / d;
		Ogre::Real b = vu.dotProduct(va)*n / d;
		Ogre::Real t = vu.dotProduct(vc)*n / d;

		// Create the composite projection matrix

		// Original projection matrix
		Ogre::Matrix4 P = Ogre::Matrix4(
			(2.0*n) / (r - l), 0, (r + l) / (r - l), 0,
			0, (2.0*n) / (t - b), (t + b) / (t - b), 0,
			0, 0, -(f + n) / (f - n), -(2.0*f*n) / (f - n),
			0, 0, -1, 0);

		// Rotation matrix
		Ogre::Matrix4 M = Ogre::Matrix4(
			vr.x, vu.x, vn.x, 0,
			vr.y, vu.y, vn.y, 0,
			vr.z, vu.z, vn.z, 0,
			0, 0, 0, 1);

		// Translation matrix
		Ogre::Matrix4 T = Ogre::Matrix4(
			1, 0, 0, -pe.x,
			0, 1, 0, -pe.y,
			0, 0, 1, -pe.z,
			0, 0, 0, 1);

		Ogre::Matrix4 offAxis = P*M.transpose()*T;

		mCameras[i]->setCustomProjectionMatrix(true, offAxis);
	}
}

Ogre::SceneManager* OgreApplication::getSceneManager(void){
	return mSceneMgr;
}

void OgreApplication::setBackground(double r, double g, double b){
	// Configure the viewport
	for (auto viewport : mViewports){
		viewport->setBackgroundColour(Ogre::ColourValue(r, g, b));
	}
}

void OgreApplication::setupResources(Ogre::String resourcesCfg)
{
	// Load resource paths from config file
	Ogre::ConfigFile cf;
	cf.load(resourcesCfg);

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

void OgreApplication::setup(void)
{
	mRoot = new Ogre::Root("plugins.cfg");

	setupResources("resources.cfg");

	if (mRoot->restoreConfig())
	{
		createWindows();
	}
	else
	{
		throw std::runtime_error("Could not restore Ogre3D config.");
	}

	// Get the SceneManager, in this case a generic one
	mSceneMgr = mRoot->createSceneManager(Ogre::ST_GENERIC);

	// Initialize the OverlaySystem (changed for Ogre 1.9)
	mOverlaySystem = new Ogre::OverlaySystem();
	mSceneMgr->addRenderQueueListener(mOverlaySystem);

	// Create all cameras
	for (unsigned i = 0; i < mMonitors.size(); i++){
		Ogre::String strCameraName = "Camera" + Ogre::StringConverter::toString(i);
		mCameras.push_back(mSceneMgr->createCamera(strCameraName));
	}

	// Update the projection matrices assuming the eye is at the origin
	updateProjMatrices(0, 0, 0);

	// Create all viewports
	for (unsigned int i = 0; i < mMonitors.size(); i++){
		mViewports.push_back(mWindows[i]->addViewport(mCameras[i]));
	}

	// Set default mipmap level (NB some APIs ignore this)
	Ogre::TextureManager::getSingleton().setDefaultNumMipmaps(5);

	// Load resources
	Ogre::ResourceGroupManager::getSingleton().initialiseAllResourceGroups();
}