#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

from flystim.options import OptionParser
from random import choice

class MrDisplay:
    def __init__(self, rate=0):
        try:
            self.manager = OptionParser(description='MrDisplay', default_use_server=True).create_manager()
            self.manager.hide_corner_square()
        except:
            print('Not using visual stimulus.')
            self.manager = None

        self.stim_type = 'SineGrating'
        self.angles = [0,90]
        self.rate = rate

    def nextStim(self):

        if self.manager is None:
            return

        angle = choice(self.angles)
        print('Moving to next stimulus.')

        self.manager.stop_stim()
        self.manager.load_stim(name=self.stim_type, period=20, rate=self.rate, color=1.0, background=0.0, angle=angle)
        self.manager.start_stim()

def main():
    OptionParser(description='Run display server.', default_setup_name='bigrig').run_server()

if __name__ == '__main__':
    main()
