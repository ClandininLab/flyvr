import pyglet
from pyglet.gl import *
from time import sleep
from threading import Lock
from xmlrpc.server import SimpleXMLRPCServer

from flyvr.service import Service
from pyglet import clock, font

# class Hud(object):
#
#     def __init__(self, win):
#         self.win = win
#
#         helv = font.load('Helvetica', self.win.width / 15.0)
#         self.text = font.Text(
#             helv,
#             'Hello, World!',
#             x=self.win.width / 2,
#             y=self.win.height / 2,
#             halign=font.Text.CENTER,
#             valign=font.Text.CENTER,
#             color=(1, 1, 1, 0.5),
#         )
#         self.fps = clock.ClockDisplay()
#
#     def draw(self):
#         glClear(GL_COLOR_BUFFER_BIT)
#         glMatrixMode(GL_PROJECTION)
#         glLoadIdentity()
#         gluOrtho2D(0, self.win.width, 0, self.win.height)
#         glMatrixMode(GL_MODELVIEW)
#         glLoadIdentity()
#         self.text.draw()
#         self.fps.draw()

class Stimulus:
    def __init__(self, level=0.5):
        self.display = pyglet.window.get_platform().get_default_display()
        self.screens = sorted(self.display.get_screens(), key=lambda screen: screen.x)

        # create dictionary of screens, indexed by direction
        self.screen_dict = {
                            'west':  self.screens[1],
                            'north': self.screens[2],
                            'east':  self.screens[3],
                            'south': self.screens[4]
                            }

        # create dictionary of windows
        self.window_dict = {dir: pyglet.window.Window(screen=screen, fullscreen=True, vsync=True)
                            for dir, screen in self.screen_dict.items()}

        # create a dictionary of cameras and huds
        # self.hud_dict = {dir: Hud(win) for dir, win in self.window_dict.items()}

        # set FPS limit
        # pyglet.clock.set_fps_limit(60)

        # communicating level change
        self.set_level(level)

    def set_level(self, value):
        for dir, win in self.window_dict.items():
            win.switch_to()

            glClearColor(value, value, value, 1)
            glClear(GL_COLOR_BUFFER_BIT)

            # win.dispatch_events()
            # self.hud_dict[dir].draw()
            # pyglet.clock.tick()

            # sleep(1/60)

            win.flip()

        return True

def main():
    stim = Stimulus()
    sleep(3)
    stim.set_level(1)
    server = SimpleXMLRPCServer(("localhost", 8000))
    print("Listening on port 8000...")
    server.register_function(stim.set_level, 'set_level')
    server.serve_forever()

if __name__=='__main__':
    main()