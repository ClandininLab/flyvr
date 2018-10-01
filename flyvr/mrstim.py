#!/usr/bin/env python3

# Example client program that walks through all available stimuli.

from flystim.options import OptionParser
from random import choice
import os

def format_values(values, delimeter='\t', line_ending='\n'):
    retval = [str(value) for value in values]
    retval = delimeter.join(retval)
    retval += line_ending

    return retval

class MrDisplay:
    def __init__(self,rate=0):
        try:
            self.manager = OptionParser(description='MrDisplay', default_use_server=True).create_manager()
            self.manager.hide_corner_square()
        except:
            print('Not using visual stimulus.')
            self.manager = None

        #self.stim_type = 'SineGrating'
        self.angles = [0,90]
        self.rate = rate

        #self.stimuli_file_name = os.path.join(exp_dir, 'stimuli.txt')

    def nextStim(self, _trial_dir):

        if self.manager is None:
            return

        stim_type = choice(['SineGrating', 'SineGrating', None])
        print('Moving to next stimulus.')

        self.manager.stop_stim()
        if stim_type is not None:
            angle = choice(self.angles)
            self.manager.load_stim(name=stim_type, period=20, rate=self.rate, color=1.0, background=0.0, angle=angle)
            self.manager.start_stim()
        else:
            angle = None

        self.stimuli_file_name = os.path.join(_trial_dir, 'stimuli.txt')
        self.stimuli_file = open(self.stimuli_file_name, 'w')
        self.stimuli_file.write(format_values([stim_type, angle]))
        self.stimuli_file.flush()
        self.stimuli_file.close()
        print('stimuli logged.')

def main():
    OptionParser(description='Run display server.', default_setup_name='bigrig').run_server()

if __name__ == '__main__':
    main()
