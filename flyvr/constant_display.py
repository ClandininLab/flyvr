import pyglet
from pyglet.gl import *
from xmlrpc.server import SimpleXMLRPCServer
from threading import Lock, Thread

class Stimulus:
    def __init__(self, level=0):
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
                            'west':  self.screens[1],
                            'north': self.screens[2],
                            'east':  self.screens[3],
                            'south': self.screens[4]
                            }

        # create dictionary of windows
        self.window_dict = {dir: pyglet.window.Window(screen=screen, fullscreen=True, vsync=False)
                            for dir, screen in self.screen_dict.items()}

        # set up window drawing routine
        for dir, win in self.window_dict.items():
            @win.event
            def on_draw(dir=dir, win=win):
                level = self.level
                glClearColor(level, level, level, 1)
                win.clear()

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
    pyglet.clock.schedule_interval(int, 1. / 60)
    pyglet.app.run()

if __name__=='__main__':
    main()