from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

windows = [0]*4

def initFun():
    glClearColor(1.0, 1.0, 1.0, 0.0)
    glColor3f(0.0, 0.0, 0.0)
    glPointSize(4.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0.0, 640.0, 0.0, 480.0)


def displayFun():
    glClear(GL_COLOR_BUFFER_BIT)
    glBegin(GL_POINTS)
    glVertex2i(100, 50)
    glVertex2i(100, 130)
    glVertex2i(150, 130)
    glEnd()
    glFlush()


if __name__ == '__main__':
    glutInit()

    offset = 1680
    width = 1280
    height = 720

    for k in range(4):
        glutInitWindowSize(width, height)
        glutInitWindowPosition(1680+width*k, 0)
        glutCreateWindow(b'noobtuts.com')
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
        glutDisplayFunc(displayFun)
    initFun()

    glutMainLoop()