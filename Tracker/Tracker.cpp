// Tracker.cpp : main project file.

#include "stdafx.h"

#include "TutorialApplication.h"

#include <windows.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

#include "arduino.h"
#include "timer.h"

#pragma comment(lib, "user32.lib")

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;
using namespace cv;

// Global variables containing the move command
double xMove = 0.0;
double yMove = 0.0;

// Global variables containing the last known GRBL position
double xStatus = 0.0;
double yStatus = 0.0;

// Global variable used to signal when serial port should close
bool killSerial = false;

// Global variable used to signal when the Ogre3D window should close
bool kill3D = false;

// Global variable used to indicate when the Ogre3D engine is running
bool readyFor3D = false;

// Mutex to manage access to xMove and yMove
HANDLE coordMutex;

// Mutex to manage access to 3D graphics variables
HANDLE gfxMutex;
double cameraX=0, cameraY=47, cameraZ=222;

DWORD WINAPI SerialThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);

	// Create the timer
	DebugTimer^ loopTimer = gcnew DebugTimer("serial_loop_time.txt");

	GrblBoard ^grbl;
	GrblStatus status;

	double xMoveLocal = 0.0;
	double yMoveLocal = 0.0;

	// Connect to GRBL
	grbl = gcnew GrblBoard();

	// Continually poll GRBL status and move if desired
	while (!killSerial){
		loopTimer->Tick();

		// Read the current status
		status = grbl->ReadStatus();

		// Lock access to global coordinates
		WaitForSingleObject(coordMutex, INFINITE);

		// Read out the move command and reset it to zero
		xMoveLocal = xMove;
		yMoveLocal = yMove;
		xMove = 0.0;
		yMove = 0.0;

		// Update the GRBL position
		xStatus = status.x;
		yStatus = status.y;

		// Release access to xMove and yMove
		ReleaseMutex(coordMutex);

		// Run the move command if applicable
		if ((xMoveLocal != 0.0 || yMoveLocal != 0.0) && !status.isMoving){
			grbl->Move(xMoveLocal, yMoveLocal);
		}

		loopTimer->Tock();
	}

	// Close streams
	loopTimer->Close();
	grbl->Close();

	return TRUE;
}

// clamp "value" between "min" and "max"
double clamp(double value, double min, double max){
	if (abs(value) < min){
		return 0.0;
	}
	else if (value < -max){
		return -max;
	}
	else if (value > max) {
		return max;
	}
	else {
		return value;
	}
}

DWORD WINAPI GraphicsThread(LPVOID lpParam){
	// lpParam not used in this example
	UNREFERENCED_PARAMETER(lpParam);
	TutorialApplication app;
	double cameraX_local, cameraY_local, cameraZ_local;
	try {
		app.go();
		readyFor3D = true;
		while (!kill3D){
			// Copy over the camera position information
			WaitForSingleObject(gfxMutex, INFINITE);
			cameraX_local = cameraX;
			cameraY_local = cameraY;
			cameraZ_local = cameraZ;
			ReleaseMutex(gfxMutex);

			// Move the camera
			app.setCameraPosition(cameraX_local, cameraY_local, cameraZ_local);

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

int main() {
	
	// Create the timer
	DebugTimer^ loopTimer = gcnew DebugTimer("main_loop_time.txt");

	// Create the mutexes
	coordMutex = CreateMutex(NULL, FALSE, NULL);
	gfxMutex = CreateMutex(NULL, FALSE, NULL);

	// Start the serial thread
	HANDLE serialThread;
	DWORD serThreadID;
	serialThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)SerialThread, NULL, 0, &serThreadID);
	
	// Create the graphics thread
	HANDLE graphicsThread;
	DWORD gfxThreadID;
	graphicsThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)GraphicsThread, NULL, 0, &gfxThreadID);

	// Wait for 3D engine to be up and running
	while (!readyFor3D);
	
	// Options
	int width = 200;
	int height = 200;
	int blur_size = 10;
	int buffer = blur_size;
	int cropped_width = width - 2 * buffer;
	int cropped_height = height - 2 * buffer;

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, width);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, height);

	// Original, unprocessed, captured frame from the camera.
	Mat im, src;
	RotatedRect box;
	vector<vector<Point>> contours;
	vector<Vec4i> hierarchy;

	double xCam, yCam, xMoveLocal, yMoveLocal, aCam;
	double xStatusLocal, yStatusLocal;

	double minMove = 1;
	double maxMove = 40;

	for (int i = 0; i < 10000; i++){
		loopTimer->Tick();

		// Read image
		cap.read(src);

		// Crop, convert to grayscale, threshold
		cvtColor(src, im, CV_BGR2GRAY);
		blur(im, im, Size(blur_size, blur_size));
		im = im(Rect(buffer, buffer, cropped_width, cropped_height));
		threshold(im, im, 110, 255, THRESH_BINARY_INV);

		// Detect contours
		findContours(im, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);

		// Find biggest contour
		int idx_max = -1;
		size_t size_max = 0;
		for (int idx = 0; idx < contours.size(); idx++){
			if (contours[idx].size() > size_max){
				size_max = contours[idx].size();
				idx_max = idx;
			}
		}

		// Fit ellipse
		if (size_max > 5){
			box = fitEllipse(Mat(contours[idx_max]));
			src = src(Rect(buffer, buffer, cropped_width, cropped_height));
			ellipse(src, box, Scalar(0,0,255), 2, 8);
			//imshow("Result", src);
			//waitKey(1);
		} else {
			loopTimer->Tock("0.000,0.000,0.000,0.000,0.000,{0:0.000}");
			src = src(Rect(buffer, buffer, cropped_width, cropped_height));
			//imshow("Result", src);
			//waitKey(1);
			continue;
		}

		// Calculate coordinates of the dot with respect to the center of the frame
		xCam = box.center.x - cropped_width/2.0;
		yCam = box.center.y - cropped_height/2.0;
		aCam = box.angle;

		// Scale coordinates to mm
		xCam = xCam / 9.1051;
		yCam = yCam / 9.1051;

		// Calculate move command
		xMoveLocal = clamp(-xCam, minMove, maxMove);
		yMoveLocal = clamp(yCam, minMove, maxMove);

		// Lock access to coordinate data
		WaitForSingleObject(coordMutex, INFINITE);

		xMove = xMoveLocal;
		yMove = yMoveLocal;

		xStatusLocal = xStatus;
		yStatusLocal = yStatus;

		// Release access to coordinate data
		ReleaseMutex(coordMutex);

		// Update camera display
		WaitForSingleObject(gfxMutex, INFINITE);
		cameraX = yStatusLocal + yCam + 85.175;
		cameraY = 47;
		cameraZ = xStatusLocal - xCam + 715;
		ReleaseMutex(gfxMutex);

		// Format data for logging
		System::String^ format = System::String::Format("{0:0.000},{1:0.000},{2:0.000},{3:0.000},{4:0.000},{{0:0.000}}", 
			xCam, yCam, xStatusLocal, yStatusLocal, aCam);

		// Log data
		loopTimer->Tock(format);
	}
	
	// Close streams
	loopTimer->Close();

	// Kill the serial thread
	killSerial = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(serialThread, INFINITE);

	// Close the handles to the mutexes and serial thread
	CloseHandle(serialThread);
	CloseHandle(coordMutex);

	// Kill the 3D graphics thread
	kill3D = true;

	// Wait for serial thread to terminate
	WaitForSingleObject(graphicsThread, INFINITE);

	// Close the handles to the mutexes and graphics thread
	CloseHandle(graphicsThread);
	CloseHandle(gfxMutex);

	return 0;
}

/*
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
switch (uMsg)
{
case WM_CREATE:
{
PIXELFORMATDESCRIPTOR pfd =
{
sizeof(PIXELFORMATDESCRIPTOR),
1,
PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER,    //Flags
PFD_TYPE_RGBA,            //The kind of framebuffer. RGBA or palette.
32,                        //Colordepth of the framebuffer.
0, 0, 0, 0, 0, 0,
0,
0,
0,
0, 0, 0, 0,
24,                        //Number of bits for the depthbuffer
8,                        //Number of bits for the stencilbuffer
0,                        //Number of Aux buffers in the framebuffer.
PFD_MAIN_PLANE,
0,
0, 0, 0
};

HDC hdc = GetDC(hwnd);

int pixel_format_num = ChoosePixelFormat(hdc, &pfd);
SetPixelFormat(hdc, pixel_format_num, &pfd);

}
break;

default:
return DefWindowProc(hwnd, uMsg, wParam, lParam);
}
return 0;
}

BOOL CALLBACK MonitorEnumProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData)
{

int *monitor_num = (int*)dwData;

MONITORINFOEX monitor_info;
ZeroMemory(&monitor_info, sizeof(MONITORINFOEX));
monitor_info.cbSize = sizeof(MONITORINFOEX);

bool success = GetMonitorInfo(hMonitor, &monitor_info);
if (success) {
wprintf(L"Device Name of Monitor: %s\n", monitor_info.szDevice);
POINT monitorTopLeft;
int width = abs(abs(monitor_info.rcMonitor.left) - abs(monitor_info.rcMonitor.right));
int height = abs(abs(monitor_info.rcMonitor.top) - abs(monitor_info.rcMonitor.bottom));
monitorTopLeft.x = monitor_info.rcMonitor.left;
monitorTopLeft.y = monitor_info.rcMonitor.top;
if (monitorTopLeft.x == 0 && monitorTopLeft.y == 0) {
return TRUE;
}
HWND hwnd = CreateWindow(wc.lpszClassName, L"opengl_window", WS_OVERLAPPEDWINDOW|WS_VISIBLE, monitorTopLeft.x, monitorTopLeft.y, width, height, NULL, NULL, wc.hInstance, NULL);
if (hwnd) {
window_handles[*monitor_num] = hwnd;
HDC hdc = GetWindowDC(hwnd);

if (hdc) {
device_context_handles[*monitor_num] = hdc;
} else {
printf("FAIL TO GET HDC\n");
}

} else {
printf("FAIL TO GET HWND\n");
}
}
(*monitor_num)++;
return TRUE;
}
*/

//	HINSTANCE hInstance = GetModuleHandle(NULL);
//	if (!hInstance) {
//		printf("NOT VALID HINSTANCE\n");
//	}
//
//	wc.style = CS_OWNDC;
//	wc.lpfnWndProc = WindowProc;
//	wc.hInstance = hInstance;
//	wc.hbrBackground = (HBRUSH)(COLOR_BACKGROUND);
//	wc.lpszClassName = L"opengl_window";
//	if (!RegisterClass(&wc)) {
//		printf("COULD NOT REGISTER CLASS\n");
//	}
//
//	char *myargv[1];
//	int myargc = 1;
//	myargv[0] = _strdup("Myappname");
//	glutInit(&myargc, myargv);
//	glutInitDisplayMode(GLUT_DEPTH | GLUT_DOUBLE | GLUT_RGBA);
//
//	int monitor_num = 0;
//	EnumDisplayMonitors(NULL, NULL, MonitorEnumProc, (LPARAM)&monitor_num);
//
//	num_context = monitor_num;
//	for (int m_num = 0; m_num < num_context; m_num++) {
//		HWND curr_hwnd = window_handles[m_num];
//		if (IsWindow(curr_hwnd)) {
//			printf("VALID WINDOW\n");
//		}
//		else {
//			printf("INVALID WINDOW #%d", m_num);
//		}
//		HDC curr_hdc = device_context_handles[m_num];
//		HGLRC curr_hglrc = wglCreateContext(curr_hdc);
//		render_context_handles[m_num] = curr_hglrc;
//		if (wglMakeCurrent(curr_hdc, curr_hglrc)) {
//			//glewInit();
//		}
//	}
//
//	// Start threads
//	//HANDLE camera_display_handle = (HANDLE) _beginthread(cameraDisplayLoop, 0, &capped_frame); // Hopefully this allows the camera display to work without slowing down the main loop
//	// @@@@@@ MAIN LOOP @@@@@@
//			
//				if (get_counter() - screen_update_timer >= 8)
//				{
//					for (int rc_num = 0; rc_num < num_context; rc_num++) {
//						HGLRC curr_hglrc = render_context_handles[rc_num];
//						HDC curr_hdc = device_context_handles[rc_num];
//						if (wglMakeCurrent(curr_hdc, curr_hglrc)) {
//							draw_cylinder_bars(rc_num, closed_loop_stimulus);
//						}
//					}
//
//					screen_update_timer = get_counter();
//				}
//

//	//CloseHandle(camera_display_handle);
//
//
//	arduino->Close();
//
//	return 0;

