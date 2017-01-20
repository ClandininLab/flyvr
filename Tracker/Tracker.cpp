// Tracker.cpp : main project file.

#include "stdafx.h"
#include "arduino.h"
#include "glew.h"
#include "freeglut.h"
#include <stdio.h>
#include <iostream>
#include <string>
#include <fstream>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/features2d/features2d.hpp>

#include <windows.h>

#pragma comment(lib, "user32.lib")

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;
using namespace std;
using namespace cv;

using namespace System::Text::RegularExpressions;

// Global variables related to GLUT because GLUT is dumb and requires use of global variables like this
/*
FlyPosition fly_position;
int windows[4], window1, window2, window3, window4;
int num_context;
HWND window_handles[4], hwnd1, hwnd2, hwnd3, hwnd4;
HDC device_context_handles[4], hdc1, hdc2, hdc3, hdc4;
HGLRC render_context_handles[4], hrc1, hrc2, hrc3, hrc4;
WNDCLASS wc;
*/

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

/// start of code from http://stackoverflow.com/questions/1739259/how-to-use-queryperformancecounter
double PCFreq = 0.0;
__int64 CounterStart = 0;

void StartCounter()
{
	LARGE_INTEGER li;
	if (!QueryPerformanceFrequency(&li))
		cout << "QueryPerformanceFrequency failed!\n";

	PCFreq = double(li.QuadPart) / 1000.0;

	QueryPerformanceCounter(&li);
	CounterStart = li.QuadPart;
}
double GetCounter()
{
	LARGE_INTEGER li;
	QueryPerformanceCounter(&li);
	return double(li.QuadPart - CounterStart) / PCFreq;
}
/// end of code from http://stackoverflow.com/questions/1739259/how-to-use-queryperformancecounter

int main() {
	SerialPort ^arduino;
	GrblBoard ^grbl;
	GrblStatus status;

	ofstream loop_time_file;
	loop_time_file.open("loop_time.txt");

	// Open the serial port connection to Arduino
	arduino = gcnew SerialPort("COM4", 400000);
	arduino->Open();
	Sleep(10);

	// Initialize settings of GrblBoard
	grbl = gcnew GrblBoard(arduino);
	grbl->Init();

	// Set up video capture
	VideoCapture cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
	cap.set(CV_CAP_PROP_FRAME_WIDTH, 200);
	cap.set(CV_CAP_PROP_FRAME_HEIGHT, 200);

	// Original, unprocessed, captured frame from the camera.
	Mat im;
	Mat im_with_keypoints;
	SimpleBlobDetector detector;
	std::vector<KeyPoint> keypoints;

	double minErr = 5;
	double maxMove = 40;

	double LoopTime;

	for(int i=0; i<2000; i++){
		StartCounter();
		cap.read(im);

		cvtColor(im, im, CV_BGR2GRAY);
		blur(im, im, Size(10, 10));
		detector.detect(im, keypoints);

		// drawKeypoints(im, keypoints, im_with_keypoints, Scalar(0, 0, 255), DrawMatchesFlags::DRAW_RICH_KEYPOINTS);
		// imshow("keypoints", im_with_keypoints);

		if (keypoints.size() == 0){
			continue;
		}		

		double X = keypoints[0].pt.x - 200.0 / 2;
		double Y = keypoints[0].pt.y - 200.0 / 2;

		// Console::WriteLine(System::String::Format("X={0:0.000},Y={1:0.000}", X, Y));

		status = grbl->ReadStatus();

		if ((abs(X)>minErr || abs(Y)>minErr) && !status.isMoving){

			double xMove = -X / 4.08;
			double yMove = Y / 4.08;

			xMove = xMove > maxMove ? maxMove : xMove;
			xMove = xMove < -maxMove ? -maxMove : xMove;

			yMove = yMove > maxMove ? maxMove : yMove;
			yMove = yMove < -maxMove ? -maxMove : yMove;
			
			grbl->Move(xMove, yMove);
		}
		LoopTime = GetCounter();
		loop_time_file << LoopTime << "\n";
	}

	// Close the serial port connection to Arduino
	arduino->Close();
	loop_time_file.close();

	// Pause before exiting so the console output may be reviewed
	// system("pause");
	return 0;

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
}

