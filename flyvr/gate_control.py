#!/usr/bin/env python
 
from threading import Thread, Lock
import serial
import time
import collections
import struct
import numpy as np
import scipy
import sys
from scipy import ndimage
from scipy import signal
import skimage
from skimage import filters
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import platform

from flyvr.rpc import Server
from jsonrpc import Dispatcher

class FlyDispenser:
    def __init__(self):
        self.t0=time.time()
        self.baud = 115200
        self.rawData = np.zeros(128)
        self.current_frame = np.zeros(128)
        self.previous_frame = np.ones(128)
        self.all_data = []
        self.to_display1 = np.random.rand(128,128)*255
        self.to_display2 = np.random.rand(128,128)*255
        self.isRun = True
        self.isReceiving = False
        self.camera_thread = None
        self.num_pixels = 128
        self.delay_length = 1
        self.first_delay_length = 5
        self.fly_threshold = 5
        self.num_needed_pixels = 2
        self.half_gate_width = 7
        self.gate_thresh = 100
        self.open_times = []
        self.close_times = []

        self.flyReleaseLock = Lock()

        if platform.system() == 'Darwin':
            self.port = '/dev/tty.usbmodem1411'
        else:
            self.port = 'COM4'

        print('Trying to connect to: ' + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(self.port, self.baud, timeout=4)
            print('Connected to ' + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')
        except:
            raise Exception("Failed to connect with " + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')
 
    def readSerialStart(self):
        if self.camera_thread == None:

            #Start camera thread
            self.camera_thread = Thread(target=self.backgroundThreadCamera)
            self.camera_thread.start()

            # Block until we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)

    def setup_gate(self):
        #estabilsh closed gate appearance
        self.serialConnection.write(bytes([0])) #close gate
        time.sleep(3) #wait to stabilize (3sec is overkill)
        self.background_close = np.median(np.asarray(self.all_data)[-3:,:],axis=0) #save frame

        #estabilsh open gate appearance
        self.serialConnection.write(bytes([1])) #open gate
        time.sleep(3) #wait to stabilize (3sec is overkill)
        self.background_open = np.median(np.asarray(self.all_data)[-3:,:],axis=0) #save frame

        #find gate
        self.gate_difference = self.background_open - self.background_close
        self.gate_center = np.argmax(self.gate_difference)
        self.gate_start = self.gate_center-self.half_gate_width
        self.gate_end = self.gate_center+self.half_gate_width

        #for fly detection later
        self.gate_region = self.background_open[self.gate_start:self.gate_end]

        print('gate start: ', self.gate_start)
        print('gate end', self.gate_end)

    def check_gate(self):
        gate_difference = self.gate_region-self.current_frame[self.gate_start:self.gate_end]
        gate_sum = np.sum(gate_difference)
        self.gate_clear = gate_sum<self.gate_thresh

    def check_fly_passed(self):
        if (np.sum(np.abs(self.diff[self.gate_end:]) > self.fly_threshold)>self.num_needed_pixels):
            self.fly_passed = True
        else:
            self.fly_passed = False

    def look_for_fly(self):
        while(self.isRun and self.found_fly == False):
            time.sleep(0.01)

            self.check_gate()
            self.check_fly_passed()

            if (self.gate_clear == True) and (self.fly_passed == True):
                self.found_fly = True

    def getSerialData(self, frame, lines1, lines2):


        self.to_display1 = np.roll(self.to_display1, 1, axis = 0)
        self.to_display1[0] = self.current_frame
        lines1.set_data(self.to_display1)

        self.to_display2 = np.roll(self.to_display2, 1, axis = 0)
        self.to_display2[0] = np.abs(self.diff)
        lines2.set_data(self.to_display2)

    def backgroundThreadCamera(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            start_byte = self.serialConnection.read(1)
            if int(start_byte[0]) == 0:
                for i in range(self.num_pixels):
                    pixel = self.serialConnection.read(1)
                    self.rawData[i] = int(pixel[0])
                self.current_frame = np.asarray(np.ndarray.tolist(self.rawData))
                self.all_data.append(self.current_frame)
                self.diff = self.current_frame - self.previous_frame
                self.previous_frame = self.current_frame
                self.t1=time.time()
            self.isReceiving = True

    def releaseFly(self):

        def target():
            if not self.flyReleaseLock.acquire(blocking=False):
                return

            self.found_fly = False
            self.serialConnection.write(bytes([1])) # open gate
            self.open_times.append(time.time()-self.t0) # for posthoc performance analysis
            time.sleep(1)
            self.look_for_fly() # look for fly
            self.serialConnection.write(bytes([0])) # close gate
            self.close_times.append(time.time()-self.t0) # for posthoc performance analysis
            time.sleep(self.delay_length) #temp wait for testing

            self.flyReleaseLock.release()

        thread = Thread(target=target)
        thread.setDaemon(True)
        thread.start()

    def close(self):
        self.time1 = time.time()
        print(np.shape(self.all_data))
        print(self.time1-self.t0)
        self.isRun = False
        np.save('raw_gate_data', np.asarray(self.all_data))
        np.savetxt('open_data.txt', self.open_times)
        np.savetxt('close_data.txt', self.close_times)
        self.camera_thread.join()
        self.serialConnection.write(bytes([0]))
        self.serialConnection.close()
        print('Disconnected...')

def main():
    if len(sys.argv) > 1:
        plot = sys.argv[1]
    else:
        plot = 'True'

    s = FlyDispenser()   # create serial object
    s.readSerialStart()   # starts background threads

    def fly_release_target():
        s.setup_gate()

        dispatcher = Dispatcher()
        dispatcher.add_method(s.releaseFly)
        server = Server(dispatcher)

        while True:
            server.process()
            time.sleep(0.01)

    fly_release_thread = Thread(target=fly_release_target)
    fly_release_thread.setDaemon(True)
    fly_release_thread.start()

    if plot == 'True': #optional plotting code
        pltInterval = 10 # Period at which the plot animation updates [ms]
        xmin = 0
        xmax = 256
        ymin = -(1)
        ymax = 256
        fig, (ax1, ax2) = plt.subplots(1,2,sharey=True)
        line1 = ax1.matshow(np.random.rand(128,128)*255)
        line2 = ax2.matshow(np.random.rand(128,128)*255)
        anim = animation.FuncAnimation(fig, s.getSerialData, fargs=(line1,line2), interval=pltInterval)    # fargs has to be a tuple

        try:
            plt.show()
        except AttributeError:
            print('TODO: Fix AttributeError that occurs during FuncAnimation shutdown.')

    #####To do: flyvr triggers close sequence
    #time.sleep(60) #delay for testing - remove when flyvr has control
    s.close()

if __name__ == '__main__':
    main()