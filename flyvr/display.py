import pyglet
from pyglet.gl import *
from time import sleep, perf_counter
from threading import Lock, Thread
from xmlrpc.server import SimpleXMLRPCServer
import numpy as np

def Point(x, y, z):
    return np.array([x,y,z])

class TvScreen:
    def __init__(self, dir, w=1.107, h=0.6226):

        if dir=='west':
            self.pa = Point(-w/2, -h/2, +w/2) # lower left
            self.pb = Point(-w/2, -h/2, -w/2) # lower right
            self.pc = Point(-w/2, +h/2, +w/2) # upper left
        elif dir == 'north':
            self.pa = Point(-w/2, -h/2, -w/2) # lower left
            self.pb = Point(+w/2, -h/2, -w/2) # lower right
            self.pc = Point(-w/2, +h/2, -w/2) # upper left
        elif dir == 'east':
            self.pa = Point(+w/2, -h/2, -w/2) # lower left
            self.pb = Point(+w/2, -h/2, +w/2) # lower right
            self.pc = Point(+w/2, +h/2, -w/2) # upper left
        elif dir == 'south':
            self.pa = Point(+w/2, -h/2, +w/2) # lower left
            self.pb = Point(-w/2, -h/2, +w/2) # lower right
            self.pc = Point(+w/2, +h/2, +w/2) # upper left
        else:
            raise ValueError('Invalid direction')

        # determine screen unit vectors
        self.vr = self.pb - self.pa
        self.vr /= np.linalg.norm(self.vr)

        self.vu = self.pc - self.pa
        self.vu /= np.linalg.norm(self.vu)

        self.vn = np.cross(self.vr, self.vu)
        self.vn /= np.linalg.norm(self.vn)

        # Rotation matrix
        self.M = np.array([
            [self.vr[0], self.vu[0], self.vn[0], 0],
            [self.vr[1], self.vu[1], self.vn[1], 0],
            [self.vr[2], self.vu[2], self.vn[2], 0],
            [0, 0, 0, 1]])

    def get_matrix(self, pe=None, n=1e-2, f=100):
        # reference: http://csc.lsu.edu/~kooima/articles/genperspective/

        # set defaults
        if pe is None:
            pe = Point(0, 0, 0)

        # Determine frustum extents
        va = self.pa - pe
        vb = self.pb - pe
        vc = self.pc - pe

        # Determine distance to screen
        d = -np.dot(self.vn, va)

        # Compute screen coordinates
        l = np.dot(self.vr, va) * n/d
        r = np.dot(self.vr, vb) * n/d
        b = np.dot(self.vu, va) * n/d
        t = np.dot(self.vu, vc) * n/d

        # Projection matrix
        P = np.array([
            [(2.0*n) / (r - l), 0, (r + l) / (r - l), 0],
            [0, (2.0*n) / (t - b), (t + b) / (t - b), 0],
            [0, 0, -(f + n) / (f - n), -(2.0*f*n) / (f - n)],
            [0, 0, -1, 0]])

        # Translation matrix
        T = np.array([
            [1, 0, 0, -pe[0]],
            [0, 1, 0, -pe[1]],
            [0, 0, 1, -pe[2]],
            [0, 0, 0, 1]])

        offAxis = np.dot(np.dot(P, self.M.T), T)

        return offAxis

class Stimulus:
    def __init__(self, level=0.5):
        # save settings
        self.levelLock = Lock()
        self._level = level

        # set up level server
        self.setup_server()

        # create display and screens
        self.display = pyglet.window.get_platform().get_default_display()
        self.screens = sorted(self.display.get_screens(), key=lambda screen: screen.x)

        # create dictionary of screens, indexed by direction
        self.screen_dict = {
                            'west':  self.screens[2],
                            'north': self.screens[1],
                            'east':  self.screens[4],
                            'south': self.screens[3]
                            }
        self.tv_dict = {dir: TvScreen(dir) for dir in self.screen_dict.keys()}

        # create dictionary of windows
        self.window_dict = {dir: pyglet.window.Window(screen=screen, fullscreen=True, vsync=False)
                            for dir, screen in self.screen_dict.items()}

        # set up window drawing routine
        for dir, win in self.window_dict.items():
            fps_display = pyglet.window.FPSDisplay(win)
            @win.event
            def on_draw(dir=dir, win=win, fps_display=fps_display):
                #level = self.level
                #glClearColor(level, level, level, 1)
                #win.clear()

                # clear screen
                glClear(GL_COLOR_BUFFER_BIT)

                # load projection matrix for this screen
                np_mat = self.tv_dict[dir].get_matrix()
                gl_mat = map(float, np_mat.T.flat)
                gl_mat = (GLfloat * 16)(*gl_mat)
                glMatrixMode(gl.GL_PROJECTION)
                glLoadMatrixf(gl_mat)
                glDisable(gl.GL_DEPTH_TEST)

                glMatrixMode(gl.GL_MODELVIEW)

                glColor3f(0.25, 0, 0)

                glBegin(GL_QUADS)
                glVertex3f(-0.1, -3, -3)
                glVertex3f(0.1, -3, -3)
                glVertex3f(0.1, +3, -3)
                glVertex3f(-0.1, +3, -3)
                glEnd()

                glLoadIdentity()
                glRotatef(90, 0, 1, 0)

    def setup_server(self, port=54357):
        def set_level(value):
            self.level = value
            return True

        def server_func():
            server = SimpleXMLRPCServer(('localhost', port))
            print('Listening on port {}...'.format(port))
            server.register_function(set_level, 'set_level')
            server.serve_forever()
        Thread(target=server_func).start()

    def update(self, dt):
        pass

    @property
    def level(self):
        with self.levelLock:
            return self._level

    @level.setter
    def level(self, value):
        with self.levelLock:
            self._level = value

def main():
    stim = Stimulus()
    pyglet.clock.schedule_interval(stim.update, 1. / 1000)
    pyglet.app.run()

if __name__=='__main__':
    main()