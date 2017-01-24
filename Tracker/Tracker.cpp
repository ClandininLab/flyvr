// Tracker.cpp : main project file.

#include "stdafx.h"

#include <windows.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

#include "glew.h"
#include "freeglut.h"

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

// Mutex to manage access to xMove and yMove
HANDLE coordMutex;

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

int main() {
	// Create the timer
	DebugTimer^ loopTimer = gcnew DebugTimer("main_loop_time.txt");

	// Create the mutexes
	coordMutex = CreateMutex(NULL, FALSE, NULL);

	// Start the serial thread
	HANDLE serialThread;
	DWORD ThreadID;
	serialThread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)SerialThread, NULL, 0, &ThreadID);

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, 200);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, 200);

	// Original, unprocessed, captured frame from the camera.
	Mat im;
	Mat im_with_keypoints;
	SimpleBlobDetector detector;
	std::vector<KeyPoint> keypoints;

	double xCam, yCam, xMoveLocal, yMoveLocal;
	double xStatusLocal, yStatusLocal;

	double minMove = 1;
	double maxMove = 40;

	for (int i = 0; i < 5000; i++){
		loopTimer->Tick();

		// Perform image processing
		cap.read(im);
		cvtColor(im, im, CV_BGR2GRAY);
		blur(im, im, Size(10, 10));
		detector.detect(im, keypoints);

		//drawKeypoints(im, keypoints, im_with_keypoints, Scalar(0, 0, 255), DrawMatchesFlags::DRAW_RICH_KEYPOINTS);
		//imshow("keypoints", im_with_keypoints);
		//waitKey(1);

		if (keypoints.size() == 0){
			loopTimer->Tock("0.000,0.000,0.000,0.000,{0:0.000}");
			continue;
		}

		// Calculate coordinates of the dot with respect to the center of the frame
		xCam = keypoints[0].pt.x - 200.0/2;
		yCam = keypoints[0].pt.y - 200.0/2;

		// Scale coordinates to mm
		xCam = xCam / 4.471;
		yCam = yCam / 4.471;

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

		// Format data for logging
		System::String^ format = System::String::Format("{0:0.000},{1:0.000},{2:0.000},{3:0.000},{{0:0.000}}", 
			xCam, yCam, xStatusLocal, yStatusLocal);

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

