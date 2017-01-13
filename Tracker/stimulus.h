extern int window1, window2, window3, window4;

struct FlyPosition
{
	double x=0;
	double y=0;
	double theta=0;
};

// This must be declared as a global variable to work with the GLUT rendering function
extern FlyPosition fly_position;

/*
All the stimulus function headers go here
*/

void draw_cylinder_bars(int window_num, bool closed_loop);
void change_size(int w, int h);