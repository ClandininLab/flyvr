# tracker

## Introduction

Program to track flies with an overhead camera mounted on a CNC rig.  TVs surrounding the fly provide visual stimuli that react to the fly's position.

## Instructions

These instructions assume a Windows build platform.

```
> git clone https://github.com/ClandininLab/tracker.git
> cd tracker
> mkdir build
> cd build
```
For a optimized (Release) build:
```
> cmake .. -G "Visual Studio 14 Win64"
> cmake --build . --target ALL_BUILD --config Release
> cd ../bin
> tracker
```

For a debug build:
```
> cmake .. -G "Visual Studio 14 Win64"
> cmake --build . --target ALL_BUILD  --config Debug
> cd ../bin
> tracker
```

## Setup

### Operating System

Install Windows 10 and update the NVidia graphics card drivers.

### Tools
1. Install [Visual Studio 2015 Community](https://www.visualstudio.com/)
    1. Be sure to install C++ Tools and Windows SDK
1. Install the latest version of [CMake](https://cmake.org/)
1. Install the latest version of [pylon](https://www.baslerweb.com/en/support/downloads/software-downloads/)

### Libraries

1. Download [SimpleINI](https://github.com/brofield/simpleini) to C:\lib\simpleini
1. Download [OpenCV 3.2](http://opencv.org/releases.html) to C:\lib\opencv
1. From this [forum post](http://ogre3d.org/forums/viewtopic.php?t=69274) install the following:
    1. [BOOST](https://goo.gl/QmGS7N) to C:\lib\boost
    1. [OGRE 1.9 SDK](https://goo.gl/jzp20i) to C:\lib\ogre

### GRBL

Adapted from instructions [here](https://github.com/gnea/grbl/wiki/Compiling-Grbl)

1. Download [GRBL source code](https://github.com/gnea/grbl)
2. Modify configuration for fast communication and 2-axis homing
    1. Open config.h
    2. Change BAUD_RATE from 230400 to 400000 (around line 41)
    3. Comment out existing definitions for HOMING_CYCLE_0 and HOMING_CYCLE_1 (around lines 105-106)
    4. Uncomment definition for HOMING_CYCLE_0 that homes X and Y in one cycle (around line 110)
    5. Save and close config.h
3. Launch the Arduino IDE
4. Click the Sketch drop-down menu, navigate to Include Library and select Add .ZIP Library.
    * IMPORTANT: Be sure to select the GRBL folder inside the grbl-XXX folder, which only contains the source files and an example directory.
5. Open the GrblUpload Arduino example.
    * Click the File down-down menu, navigate to Examples->Grbl, and select GrblUpload.
6. Compile and upload Grbl to your Arduino.
    * Connect your Arduino Uno to your computer.
    * Make sure your board is set to the Arduino Uno in the Tool->Board menu and the serial port is selected correctly in Tool->Serial Port.
    * Click the Upload, and GRBL should compile and flash to your Arduino.
