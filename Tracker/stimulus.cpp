#include "stdafx.h"
#include "stimulus.h"
#include "freeglut.h"
#include "vec3.hpp"
#include "glm.hpp"
#include "gtc/matrix_transform.hpp"
#include "GLFW/glfw3.h"
#include "timer.h"
#include <math.h>
#include <cmath>
#include <stdio.h>

#define PI 3.14159265

void change_size(int w, int h)
{
	float ratio;

	// Prevent a divide by zero, when window is too short
	// (you cant make a window of zero width).
	if (h == 0)
		h = 1;

	ratio = 1.0f * w / h;
	// Reset the coordinate system before modifying
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();

	// Set the viewport to be the entire window
	glViewport(0, 0, w, h);

	// Set the clipping volume
	gluPerspective(45, ratio, 1, 1000);
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
}


void draw_cylinder_bars(int window_num, bool closed_loop)
{

	//if (window_num == 0 || window_num == 1 || window_num == 2) return;
	glLoadIdentity();
	glFlush();

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	// retrieve the window width and height for
	// the window we are rendering to
	HGLRC hglrc = wglGetCurrentContext();
	HDC hdc = wglGetCurrentDC();
	HWND hwnd = WindowFromDC(hdc);

	RECT rect;
	if (!GetWindowRect(hwnd, &rect)) {
		return;
	}
	float window_width = abs(rect.left - rect.right);
	float window_height = abs(rect.top - rect.bottom);

	float r = sqrt(pow(window_width,2)*2); // radius of cylinder
	float bar_width = 1.5f; // degrees
	float spacing_factor = 1.f;  // degrees

	double time_in_ms = get_counter();
	double direction = 1; // direction of rotation
	float degree_per_ms = 0.01; // degrees to rotate every ms

	// this rotates the camera every ms by degree_per_ms
	float target_theta = (90.f * window_num) + (time_in_ms * degree_per_ms * direction);

	// model matrix to transform from object space
	// to world space (we scale to be around size of window)
	glm::mat4 model_matrix = glm::mat4();
	model_matrix[0].x = r;
	model_matrix[1].y = r;
	model_matrix[2].z = r;

	// create the view matrix (camera matrix) to transform
	// from world space to camera space (eye space)
	glm::vec3 camera_pos = glm::vec3(0.f, 0.f, 0.f);
	
	if (closed_loop) {
		// convert fly_position to world coordinate space
		printf("fly position x: %f, fly position y: %f\n", fly_position.x, fly_position.y);
		float center_x = fly_position.x * 0.01;
		float center_y = fly_position.y * 0.01;
		printf("camera center x: %f, camera center y: %f\n", center_x, center_y);
		camera_pos = glm::vec3(-center_x, 0.f, -center_y);
	}

	glm::vec3 camera_target = glm::vec3(r*cos((90.f * window_num + 90.f) * (PI / 180.f)), 0.f, r*sin((90.f * window_num + 90.f) * (PI / 180.f)));
	glm::vec3 camera_direction = glm::normalize(camera_pos - camera_target);
	glm::vec3 camera_right = glm::normalize(glm::cross(glm::vec3(0.f, 1.f, 0.f), camera_direction));
	glm::vec3 camera_up = glm::cross(camera_direction, camera_right);
	glm::mat4 view_matrix = glm::lookAt(camera_pos, camera_target, camera_up);

	// create projection matrix to transform from camera
	// space to projection space (screen coordinates)
	float znear = (1 / 2)*r*sqrt(2);
	glm::mat4 projection_matrix = glm::perspective(glm::radians(90.f), (float)window_width / (float)window_height, 1.f, 2.f*r);

	// calculate the model, view, projection
	// matrix to apply to object space coordinates
	glm::mat4 mvp = projection_matrix * view_matrix * model_matrix;

	float theta_start = (90.f * window_num);
	float theta_end = (90.f * window_num + 180.f);

	float diff = theta_end - 360.f;

	float theta = target_theta;
	while (theta < target_theta + 360.f) {
		double theta_int;
		double theta_fract = modf(theta, &theta_int);
		float theta_new = float(int(theta_int) % 360) + float(theta_fract);
		
		theta_fract = modf(theta+bar_width, &theta_int);
		float theta_barwidth = float(int(theta_int) % 360) + float(theta_fract);

		if (diff > 0) {
			if (theta_new < theta_start) {
				theta_new += theta_start + diff;
			}
			if (theta_barwidth < theta_start) {
				theta_barwidth += theta_start + diff;
			}
		}

		if (((theta_new > theta_start && theta_barwidth > theta_start)) && ((theta_new < theta_end && theta_barwidth < theta_end))) {
			float x1 = cos(theta * PI / 180.f);
			float y1 = 1;
			float z1 = sin(theta * PI / 180.f);
			float x2 = cos((theta + bar_width) * PI / 180.f);
			float y2 = -1;
			float z2 = sin((theta + bar_width) * PI / 180.f);
		
			// homogenized object space coordinates
			glm::vec4 p1 = glm::vec4(x1, y1, z1, 1); // top left
			glm::vec4 p2 = glm::vec4(x1, y2, z1, 1); // bottom left
			glm::vec4 p3 = glm::vec4(x2, y2, z2, 1); // bottom right
			glm::vec4 p4 = glm::vec4(x2, y1, z2, 1); // top right

			// homogenized projection space coordinates
			glm::vec4 p1_proj = mvp * p1;
			glm::vec4 p2_proj = mvp * p2;
			glm::vec4 p3_proj = mvp * p3;
			glm::vec4 p4_proj = mvp * p4;

			// de-homogenize
			glm::vec3 p1_prime = glm::vec3(p1_proj[0], p1_proj[1], p1_proj[2]) / p1_proj[3];
			glm::vec3 p2_prime = glm::vec3(p2_proj[0], p2_proj[1], p2_proj[2]) / p2_proj[3];
			glm::vec3 p3_prime = glm::vec3(p3_proj[0], p3_proj[1], p3_proj[2]) / p3_proj[3];
			glm::vec3 p4_prime = glm::vec3(p4_proj[0], p4_proj[1], p4_proj[2]) / p4_proj[3];

			glEnable(GL_TEXTURE_2D);
			glBindTexture(GL_TEXTURE_2D, 1);
			glBegin(GL_QUADS);
			// Draw the vertices in CCW order
			glVertex3f(p1_prime[0], p1_prime[1], p1_prime[2]);
			glVertex3f(p2_prime[0], p2_prime[1], p2_prime[2]);
			glVertex3f(p3_prime[0], p3_prime[1], p3_prime[2]);
			glVertex3f(p4_prime[0], p4_prime[1], p4_prime[2]);
			glEnd();
		}


		theta += (spacing_factor + bar_width);
	}

	SwapBuffers(hdc);

	return;
};
