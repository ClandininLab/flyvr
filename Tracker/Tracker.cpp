// Tracker.cpp : main project file.

#include "stdafx.h"
#include "arduino.h"
#include "stimulus.h"
#include "glew.h"
#include "freeglut.h"
#include <stdio.h>
#include <iostream>
#include <string>
#include <fstream>

#include "timer.h"

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>

#include <windows.h>

#pragma comment(lib, "user32.lib")

using namespace System;
using namespace System::IO::Ports;
using namespace System::Threading;
using namespace std;
using namespace cv;
using SysString = System::String;

// Global variables related to GLUT because GLUT is dumb and requires use of global variables like this
FlyPosition fly_position;
int windows[4], window1, window2, window3, window4;
int num_context;
HWND window_handles[4], hwnd1, hwnd2, hwnd3, hwnd4;
HDC device_context_handles[4], hdc1, hdc2, hdc3, hdc4;
HGLRC render_context_handles[4], hrc1, hrc2, hrc3, hrc4;
WNDCLASS wc;

// This needs to be cleaned up but I gotta get this shit working
// This definition should probably go somewhere else. Also, using "ready_to_send_next_move_cmd" flag here redundantly with the same flag in the main() function
//   is probably dumb, but I don't know how to make it less dumb right now.
public ref class GrblQuery
{
public:
	GrblStatus grbl_status;
	SerialPort^ arduino;
	bool ready_to_send_next_move_cmd;
	bool completed = false;

	GrblQuery(SerialPort^ arduino_port)
	{
		arduino = arduino_port;
	}

	void QueryGrblStatus()
	{
		arduino_tx(arduino, "?"); // Query Grbl status

		SysString^ query_status_response;
		do
		{
			query_status_response = arduino_rx(arduino, 1000);
			if (query_status_response->Equals("ok\r"))
			{
				ready_to_send_next_move_cmd = true;
			}
			else
			{
				grbl_status = parse_grbl_status(query_status_response);
			}
		} while (query_status_response->Equals("ok\r"));
		completed = true;
	}
};

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

//int WINAPI WinMain( __in HINSTANCE hInstance, __in_opt HINSTANCE hPrevInstance, __in_opt LPSTR lpCmdLine, __in int nShowCmd )//(array<System::String ^> ^args)
//{
int main() {
	SerialPort ^arduino;
	GrblBoard ^grbl;

	// Open the serial port connection to Arduino
	arduino = gcnew SerialPort("COM4", 400000);
	arduino->Open();
	Sleep(10);

	grbl = gcnew GrblBoard(arduino);
	grbl->Init();

	grbl->North();
	Sleep(1000);
	grbl->South();
	Sleep(1000);
	grbl->East();
	Sleep(1000);
	grbl->West();
	Sleep(1000);

	// Close the serial port connection to Arduino
	arduino->Close();
	return 0;

//	// Set up files for testing and logging
//	ofstream loop_time_file;
//	loop_time_file.open("loop_time.txt");
//	loop_time_file << "\n";
//	ofstream data_input_time_file;
//	data_input_time_file.open("data_input_time.txt");
//	data_input_time_file << "query send time, query receive time, frame cap time, image processing time, move command send time";
//	ofstream command_time_file;
//	command_time_file.open("command_time.txt");
//	ofstream command_file;
//	command_file.open("commands.txt");
//	ofstream misc_time_file; // I just use this for logging timers that I might want to move around
//	misc_time_file.open("misc_times.txt");
//	ofstream position_file;
//	position_file.open("positions.txt");
//	VideoWriter video("out.avi", CV_FOURCC('M', 'J', 'P', 'G'), 10, Size(200, 200), true);
//
//	start_counter(); // For getting timing data
//	// Timers for stuff that might need them. Can add more later.
//	double move_init_timer = get_counter();
//	double loop_timer = get_counter(); // This is the main timer to monitor the loop
//	double command_timer = get_counter(); // Log how long it takes to write a move command into the buffer
//	double data_input_timer = get_counter(); // Log how long it takes to grab a camera frame and the motor status
//	double misc_timer = get_counter();
//	double query_timer = get_counter();
//	double arduino_command_timer = get_counter(); // Timer used to send commands to
//	double frame_cap_delay = get_counter();
//	double screen_update_timer = get_counter();
//	
//	int moves_in_queue = 0;
//
//	// Configure serial comms for Arduino
//	SysString^ port_name;
//	SysString^ serial_response;
//	SysString^ serial_message;
//
//
//
//	// Motor parameters (for Grbl)
//	double steps_per_mm_x = 40;
//	double steps_per_mm_y = 40;
//	
//	// Define some OpenCV primary colors for convenience
//	Scalar color_white = Scalar(255, 255, 255);
//	Scalar color_black = Scalar(0, 0, 0);
//	Scalar color_red = Scalar(255, 0, 0);
//	Scalar color_green = Scalar(0, 255, 0);
//	Scalar color_blue = Scalar(0, 0, 255);
//
//	// Set up image capture and processing
//	vector<vector<Point>> contours; // This is a vector of vectors, i.e. a vector of contours. You will want to work with each element individually, i.e. one contour at a time.
//	vector<Vec4i> hierarchy; // For storing contour hierarchy info (i.e. if certain contours are nested within others). Not sure if it's needed, but hey the info is there.
//	Mat capped_frame; // This is the original, unprocessed, captured frame from the camera. 
//					 // Keeping it separate from the subsequent processing because sometimes it's useful to have the original.
//	Mat processed_frame; // This is the one that will be processed and used to find contours on
//	
//	VideoCapture vid_cap(CV_CAP_ANY); // This is sufficient for a single camera setup. Otherwise, it will need to be more specific.
//	vid_cap.set(CV_CAP_PROP_FPS, 240); // Need to set the exposure time to appropriate value in Pylon Viewer as well
//	vid_cap.set(CV_CAP_PROP_FRAME_HEIGHT, 200); // 200x200 window
//	vid_cap.set(CV_CAP_PROP_FRAME_WIDTH, 200);
//
//	initialize_grbl(arduino);
//
//
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
//	// @@@@@@ MAIN LOOP SETUP @@@@@@
//	bool stream_enabled = false; // Whether or not to display streaming window for testing purposes
//								 // If I ever implement multithreading, then I might be able to turn this on permanently
//	bool stream_only = false; // Enable just for camera testing without any motion
//	bool console_enabled = false; // Enable to allow access to the console to send G-code manually to the Arduino
//								  // Streaming will be gimped if it's enabled at the same time (until I enable multithreading)
//	bool closed_loop_stimulus = false; //Enable to have stimulus update based on fly position (simulate reality)
//
//	GrblStatus grbl_status;
//	GrblQuery^ grbl_query = gcnew GrblQuery(arduino);
//
//
//	bool is_following = true; // for use when the contour leaves the frame
//	bool ready_to_send_next_move_cmd = true;
//	bool first_query = true;
//	UINT64 loop_counter = 0; // Counter for testing purposes
//	int video_counter = 0; // Write to video every x iterations of loop
//	
//	// Start threads
//	//HANDLE camera_display_handle = (HANDLE) _beginthread(cameraDisplayLoop, 0, &capped_frame); // Hopefully this allows the camera display to work without slowing down the main loop
//	// @@@@@@ MAIN LOOP @@@@@@
//	while (true)
//	{
//		if (console_enabled)
//		{
//			serial_message = Console::ReadLine();
//
//			if (serial_message->Equals("exit")) break;
//			arduino_tx(arduino, serial_message);
//
//			try
//			{
//				while (true)
//				{
//					serial_response = arduino_rx(arduino, 1000);
//					Console::WriteLine(serial_response);
//				}
//
//			}
//			catch (TimeoutException^)
//			{
//
//			}
//		}
//		else
//		{
//			// Let the full period (approx) finish to allow messages and stuff to go through
//			misc_timer = get_counter();
//			while (get_counter() - loop_timer < 0)
//			{
//				
//				// Also use this time to clear the serial buffer
//				double serial_timeout = floor(4.0 - (get_counter() - loop_timer)); // Set timeout to remainder of the wait period
//				try
//				{
//					SysString^ message = arduino_rx(arduino, serial_timeout);
//					if (message->Equals("ok\r"))
//						ready_to_send_next_move_cmd = true;
//				}
//				catch (TimeoutException^)
//				{
//					// Just let it slide and let the loop play out
//					continue;
//				}
//				
//			}
//
//			if (loop_counter > 0)
//			{
//				loop_time_file << loop_counter - 1 << ", " << get_counter() - loop_timer << "\n";
//				data_input_time_file << get_counter() - data_input_timer;
//				misc_time_file << loop_counter - 1 << ", " << get_counter() - misc_timer << "\n";
//			}
//
//			loop_timer = get_counter(); // make sure there is a full period between loops
//			data_input_time_file << "\n" << loop_counter << ", ";
//
//			data_input_timer = get_counter();
//
//			// Start new thread for command query
//			Thread^ grbl_query_thread = gcnew Thread(gcnew ThreadStart(grbl_query, &GrblQuery::QueryGrblStatus));
//			grbl_query_thread->Name = "grbl_query";
//			grbl_query_thread->Start();
//
//			
//
//			//arduino_tx(arduino, "?"); // Query Grbl status
//			//data_input_time_file << get_counter() - data_input_timer << ", ";
//
//			//SysString^ query_status_response;
//			//int grbl_state = 0;
//
//			//data_input_timer = get_counter();
//			//do
//			//{
//			//	query_status_response = arduino_rx(arduino);
//			//	if (query_status_response->Equals("ok\r"))
//			//	{
//			//		ready_to_send_next_move_cmd = true;
//			//	}
//			//	else
//			//	{
//			//		grbl_status = parse_grbl_status(query_status_response);
//			//	}
//			//} while (query_status_response->Equals("ok\r"));
//
//			//if (query_status_response->Contains("Idle"))
//			//{
//			//	grbl_state = GRBL_STATE_IDLE;
//			//}
//			//else if (query_status_response->Contains("Run"))
//			//{
//			//	grbl_state = GRBL_STATE_RUN;
//			//}
//			//else
//			//{
//			//	Console::WriteLine(query_status_response);
//			//	getchar();
//			//	goto exit_main_loop;
//			//}
//			//
//			
//			position_file << get_counter() << ", " << grbl_status.state << ", " << grbl_status.x << ", " << grbl_status.y << "\n";
//			data_input_time_file << get_counter() - data_input_timer << ", ";
//
//			data_input_timer = get_counter();
//			// The camera has a frame buffer, which means the capped frame may not be as up-to-date as we need
//			// A frame that's been sitting in the buffer can be detected by virtue of the delay it takes to capture the frame
//			// If the frame is captured too quickly, then capture another frame. Repeat until it takes more than 1ms
//			do
//			{
//				frame_cap_delay = get_counter();
//				vid_cap >> capped_frame;
//			} while (get_counter() - frame_cap_delay < 2);
//
//			if (capped_frame.empty())
//			{
//				// Frame was dropped
//				// TODO Make this more elegant in the final implementation. It will need to allow for the occasional dropped frame without a meltdown
//
//				fprintf(stderr, "ERROR: Frame is null\n");
//				getchar();
//				continue;
//			}
//
//			if (video_counter == 0)
//				video.write(capped_frame);
//			video_counter = (video_counter + 1) % 5;
//
//			grbl_query_thread->Join();
//			grbl_status = grbl_query->grbl_status;
//			if (!ready_to_send_next_move_cmd)
//				ready_to_send_next_move_cmd = grbl_query->ready_to_send_next_move_cmd;
//			data_input_time_file << get_counter() - data_input_timer << ", ";
//			
//
//			data_input_timer = get_counter();
//			// Convert to monochrome
//			cvtColor(capped_frame, processed_frame, CV_BGR2GRAY);
//			// Blur to reduce noise
//			blur(processed_frame, processed_frame, Size(10, 10));
//			// Threshold to convert to binary image for easier contouring
//			int binary_threshold = 200; // out of 255
//			threshold(processed_frame, processed_frame, binary_threshold, 255, CV_THRESH_BINARY);
//
//			// Detect edges (I don't think the thresholds are that important here since the image has already been binarized. However, they are mandatory for the function call)
//			Mat processed_frame_edges;
//			int lower_canny_threshold = 10;
//			int upper_canny_threshold = lower_canny_threshold * 10;
//			Canny(processed_frame, processed_frame_edges, lower_canny_threshold, upper_canny_threshold);
//
//			// Detect contours
//			contours.clear(); // Clear upon each new iteration of the loop
//			findContours(processed_frame_edges, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE);
//
//			// Find the largest contour by calculating all contour areas and picking the largest one
//			// TODO This doesn't work when the contour is concave, need to fix.
//			double largest_contour_area = 0;
//			double contour_area = 0;
//			vector<Point> object_external_contour;
//			for (int i = 0; i < contours.size(); i++)
//			{
//				contour_area = contourArea(contours[i]);
//				if (largest_contour_area < contour_area)
//				{
//					largest_contour_area = contour_area;
//					object_external_contour = contours[i];
//				}
//			}
//
//			// This will be the drawing displayed on the stream if it's enabled
//			Mat displayed_drawing = processed_frame; // Initialize with just the camera image. Outline and centroid will be added later
//			// Change the frame this is assigned to to change what you want to look at
//
//			Point2f origin = Point2f(100, 100); // Center of the frame. (0, 0) is usually the upper left corner. Define this because offset will be relative to "origin"
//			double dx = 0, last_dx;
//			double dy = 0, last_dy;
//			double dr = 0, last_dr;
//			if (!object_external_contour.empty()) // Only do the following if there's a contour to work with, otherwise just skip to the next frame
//			{
//				// Find and add bounding ellipse to the drawing
//				RotatedRect bounding_ellipse = fitEllipse(Mat(object_external_contour));
//				int bounding_ellipse_thickness = 2;
//				ellipse(displayed_drawing, bounding_ellipse, color_green, bounding_ellipse_thickness, 8); // add to drawing
//
//				// Find the moment (i.e. center of mass) of the contour and add it to the drawing. This will be the point that is actually followed.
//				Moments object_moment = moments(object_external_contour);
//				Point2f object_coord = Point2f(float(object_moment.m10) / float(object_moment.m00), float(object_moment.m01) / float(object_moment.m00)); // convert moment to useable coordinates
//				int moment_center_radius = 2;
//				circle(displayed_drawing, object_coord, moment_center_radius, color_green, CV_FILLED); // add to drawing
//
//
//				dx = last_dx = object_coord.x - origin.x; // Offset of the object centroid in x, the direction is negative
//				dy = last_dy = object_coord.y - origin.y; // Offset of the object centroid in y
//				dr = last_dr = sqrt(dx*dx + dy*dy);
//
//				// The 4.08 is a pixel-to-mm scaling factor (needs to be updated with final mount)
//				fly_position.x = grbl_status.x - dx/4.08;
//				fly_position.y = grbl_status.y + dy/4.08;
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
//				is_following = true;
//			}
//			else
//			{
//				if (is_following)
//				{
//					// If the camera was already following and the object has fallen off the frame, then "leap" in the same direction
//					dx = 2.0*last_dx;
//					dy = 2.0*last_dy;
//
//					is_following = false; //Just do this once because if it can't find the object anymore then I don't want the thing crashing into the hard stop
//				}
//			}
//
//			data_input_time_file << get_counter() - data_input_timer << ", ";
//			data_input_timer = get_counter();
//
//			if (stream_enabled || stream_only)
//			{
//				imshow("Frame", displayed_drawing);
//				char key_press = waitKey(1);
//				if (key_press == 27) return 0;
//			}
//
//			SysString^ gcode_command_type = "1";
//
//			if (!stream_only && !console_enabled) // Don't move stuff if I just want to look at the camera or send manual commands
//			{
//				// TODO Have the move command continue without an available contour just in the direction it was previously traveling
//
//				double x_command = fly_position.x;
//				double y_command = fly_position.y;
//
//				
//				if (ready_to_send_next_move_cmd && get_counter() - command_timer > 100 && dr > 5)
//				{
//					SysString^ gcode_command = "G" + gcode_command_type + " X" + Convert::ToString(x_command) + " Y" + Convert::ToString(y_command);
//					command_timer = get_counter();
//					arduino_tx(arduino, gcode_command);
//					moves_in_queue++;
//					command_time_file << get_counter() - command_timer << "\n";
//					ready_to_send_next_move_cmd = false;
//					
//					data_input_time_file << get_counter() - data_input_timer;
//				}
//
//				data_input_time_file << ", ";
//			}
//
//			if (console_enabled)
//			{
//				serial_message = Console::ReadLine();
//
//				if (serial_message->Equals("exit")) break;
//				arduino_tx(arduino, serial_message);
//
//				try
//				{
//					while (true)
//					{
//						serial_response = arduino_rx(arduino, 1000);
//						Console::WriteLine(serial_response);
//					}
//
//				}
//				catch (TimeoutException^)
//				{
//
//				}
//			}
//
//			loop_counter++;
//		}
//	}
//
//exit_main_loop:
//
//
//	// End threads
//	//CloseHandle(camera_display_handle);
//
//	// Close files
//	loop_time_file.close();
//	command_time_file.close();
//	data_input_time_file.close();
//	Console::Clear();
//
//
//	arduino->Close();
//
//	return 0;
}

