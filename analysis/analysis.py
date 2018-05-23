#########################
###  Import Thingies  ###
#########################

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import csv
import os
from tqdm import tqdm
import scipy
from scipy.interpolate import interp1d
%matplotlib inline

#####################
###  Import Data  ###
#####################

#need to fix speed issue...

Path = '/Users/lukebrezovec/FlyTracker/Data/exp-20171031-214433'


class Trial:
    def __init__ (self, dirName):
        self.cam = Cam(os.path.join(dirName, 'cam.txt'))
        self.cnc = Cnc(os.path.join(dirName, 'cnc.txt'))

class Cam:
    def __init__ (self, fname):
        print(fname)
        self.tvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(0,))
        self.xvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(2,))
        self.yvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(3,))
        self.pvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(1,), dtype=bool)
        self.avec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(6,))

class Cnc:
    def __init__ (self, fname):
        print(fname)
        self.tvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(0,))
        self.xvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(1,))
        self.yvec = np.genfromtxt(fname, delimiter=',',skip_header=1,usecols=(2,))

trials = [Trial(os.path.join(Path, dirName)) for dirName in os.listdir(Path) if 'trial' in dirName]

#################################################
### Create fly class and pull from trial data ###
#################################################

class Fly:
    def __init__ (self,trial,time_res=0.01):
        if np.any(trial.cam.pvec):
            # Get cam data (only time points where pvec is true, aka fly is present)
            camt = trial.cam.tvec[trial.cam.pvec]
            cama = interp1d(camt, trial.cam.avec[trial.cam.pvec])
            camx = interp1d(camt, trial.cam.xvec[trial.cam.pvec])
            camy = interp1d(camt, trial.cam.yvec[trial.cam.pvec])
            # Get cnc data
            cncx = interp1d(trial.cnc.tvec, trial.cnc.xvec)
            cncy = interp1d(trial.cnc.tvec, trial.cnc.yvec)
            tmin = max(camt[0], trial.cnc.tvec[0])
            tmax = min(camt[-1], trial.cnc.tvec[-1])
            # Pull from interpolated data at chosen time resolution
            self.t = np.arange(tmin, tmax, time_res)
            self.x = camx(self.t) + cncx(self.t)
            self.y = camy(self.t) + cncy(self.t)
            self.a = cama(self.t)
        else:
            self.t = None
            self.x = None
            self.y = None
            self.a = None

flies = [Fly(trial) for trial in trials]

#############################
### Plot all trajectories ###
#############################

fig = plt.figure(figsize=(10, 10))
for k, fly in enumerate(flies):
    if fly.x is not None and fly.y is not None:
        plt.plot(fly.x, fly.y, label = str(k))
plt.legend()
#plt.xlim(.2,.3)
#plt.ylim(.3,.4)
plt.plot(0.32405,0.3207,'ro',markersize=10)
plt.title('All Fly Trajectories')

### Ongoing angle plotting...

class FlyArrow:
    def __init__ (self,fly,xrange,yrange):
        if np.any(fly.x):
            self.x1 = fly.x-xrange/50
            self.x2 = fly.x+xrange/50
            self.y1 = fly.y-yrange/50
            self.y2 = fly.y+yrange/50
        else:
            self.x1 = None
            self.x2 = None
            self.y1 = None
            self.y2 = None
        
flyarrows = [FlyArrow(fly,xrange=0.02,yrange=0.02) for fly in flies]

fig1 = plt.figure(figsize=(10, 10))
plt.xlim(.29,.31)
plt.ylim(.34,.36)
ax1 = fig1.add_subplot(111)
for i in tqdm(range(np.size(flyarrows[1].x1))):
    ax1.add_patch(
        patches.FancyArrowPatch(
            (flyarrows[1].x1[i],
            flyarrows[1].y1[i]),
            (flyarrows[1].x2[i],
            flyarrows[1].y2[i]),
            arrowstyle='->',
            mutation_scale=10
        )
)
