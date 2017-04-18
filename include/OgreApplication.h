// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

// OgreApplication is based on the OGRE3D tutorial framework
// http://www.ogre3d.org/wiki/

#ifndef OGREAPPLICATION_H
#define OGREAPPLICATION_H

#include <mutex>
#include <thread>
#include <condition_variable>

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

// Struct to keep track of the user's real position and virtual position
struct Pose3D{
	double x, y, z;
	double pitch, yaw, roll;

	Pose3D() : x(0), y(0), z(0), pitch(0), yaw(0), roll(0) {}
};

// Used to keep track of monitors information
struct MonitorInfo{
	// Configuration information
	unsigned id;
	unsigned pixelWidth;
	unsigned pixelHeight;
	bool displayFullscreen;

	// Position information
	Ogre::Vector3 pa;
	Ogre::Vector3 pb;
	Ogre::Vector3 pc;

	// Human readable name
	std::string name;

	MonitorInfo() : id(0), pixelWidth(0), pixelHeight(0), displayFullscreen(false),
		pa(Ogre::Vector3::ZERO), pb(Ogre::Vector3::ZERO), pc(Ogre::Vector3::ZERO) {}
};

// High-level thread management for graphics operations
void StartGraphicsThread(std::string stimFile, std::string outDir);
void ReadGraphicsConfig(void);
void StopGraphicsThread(void);
void SetFlyPose3D(Pose3D flyPose3D);

// Thread used to handle graphics operations
void GraphicsThread(void);

class OgreApplication
{
public:
	OgreApplication();
	~OgreApplication(void);

	void setup(void);
	void readGraphicsConfig(const char *loc);

	void updateProjMatrices(double x, double y, double z);
	void setBackground(double r, double g, double b);

	void renderOneFrame(void);

	Ogre::SceneManager* getSceneManager(void);

	double targetLoopDuration;

private:
	void setupResources(Ogre::String resourcesCfg);
	void createWindows(void);

	// Rendering options
	double mNearClipDist;
	double mFarClipDist;

	// Top-level scene management
	Ogre::Root *mRoot;
	Ogre::SceneManager *mSceneMgr;

	// Initialization variables
	Ogre::OverlaySystem *mOverlaySystem;

	// Per-display members
	std::vector<Ogre::RenderWindow*> mWindows;
	std::vector<Ogre::Camera*> mCameras;
	std::vector<Ogre::Viewport*> mViewports;
	std::vector<MonitorInfo> mMonitors;
};

#endif