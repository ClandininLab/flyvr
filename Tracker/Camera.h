#ifndef CAMERA_H
#define CAMERA_H

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

using namespace cv;

// Camera configuration
#define CV_FRAME_WIDTH 200
#define CV_FRAME_HEIGHT 200

// Image processing parameters
#define CV_LOW_THRESH 110
#define CV_HIGH_THRESH 255
#define CV_BLUR_SIZE 10
#define CV_MIN_CONTOUR 5

// Scale factors to convert pixels to mm
#define CV_PIXEL_PER_MM (9.1051)

// Define post-blur cropping
#define CV_CROP_AMOUNT (CV_BLUR_SIZE)
#define CV_CROPPED_WIDTH (CV_FRAME_WIDTH - 2 * CV_CROP_AMOUNT)
#define CV_CROPPED_HEIGHT (CV_FRAME_HEIGHT - 2 * CV_CROP_AMOUNT)

// Global variable used to signal when the camera thread should close
bool g_killCamera = false;

// Mutex to manage access to 3D graphics variables
HANDLE g_cameraMutex;

// Handle to manage the graphics thread
HANDLE g_cameraThread;

// High-level thread management for graphics operations
void StartCameraThread();
void StopCameraThread();

// Thread used to handle graphics operations
DWORD WINAPI CameraThread(LPVOID lpParam);

// Variable to hold original and processed frames
Mat g_origFrame, g_procFrame;

// Variables related to contour search
RotatedRect g_boundingBox;
vector<vector<Point>> g_imContours;
vector<Vec4i> g_imHierarchy;

// Struct used to keep track of fly pose
struct CamPose{
	double x;
	double y;
	double angle;
};

CamPose g_camPose;

// Image processing routines
void prepFrame();
bool locateFly();
bool contourCompare(vector<Point> a, vector<Point> b);

#endif