import pyglet
from pyglet.gl import *

from time import sleep

class Stimulus:
    def __init__(self):
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
        self.window_dict = {dir: pyglet.window.Window(screen=screen, fullscreen=True)
                            for dir, screen in self.screen_dict.items()}

    def set_level(self, level):
        for window in self.window_dict.values():
            window.switch_to()
            glClearColor(level, level, level, 1)
            glClear(GL_COLOR_BUFFER_BIT)
            window.flip()

def main():
    stim = Stimulus()

    stim.set_level(0)
    while True:
        pass


if __name__=='__main__':
    main()