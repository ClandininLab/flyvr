# modified from:
# https://pythonprogramming.net/opengl-rotating-cube-example-pyopengl-tutorial/

from time import perf_counter

import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

verticies = (
    (1, -1, -1),
    (1, 1, -1),
    (-1, 1, -1),
    (-1, -1, -1),
    (1, -1, 1),
    (1, 1, 1),
    (-1, -1, 1),
    (-1, 1, 1)
    )

edges = (
    (0,1),
    (0,3),
    (0,4),
    (2,1),
    (2,3),
    (2,7),
    (6,3),
    (6,4),
    (6,7),
    (5,1),
    (5,4),
    (5,7)
    )


def Cube():
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(verticies[vertex])
    glEnd()


def main():
    pygame.init()
    display = (800,600)
    pygame.display.set_mode(display, DOUBLEBUF|OPENGL|pygame.FULLSCREEN)

    gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)

    glTranslatef(0.0,0.0, -5)

    startTime = perf_counter()
    iterCount = 0
    
    while True:
        done = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stopTime = perf_counter()
                pygame.quit()
                done = True

        if done:
            break

        glRotatef(1, 3, 1, 1)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        Cube()
        pygame.display.flip()

        iterCount += 1
        
        pygame.time.wait(5)

    deltaT = stopTime-startTime
    print('FPS: ' + str(iterCount/deltaT))

if __name__=='__main__':
    main()
