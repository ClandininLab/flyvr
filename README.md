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

## Computer Setup

These are instructions to prepare the lab compute from a fresh Windows install.

### Operating System

1. Install Windows 10
1. Install the following from the Gigabyte CD
    1. INF Update Utility
    1. Intel(R) Management Engine Software
    1. Creative Sound Driver
    1. Bigfoot Networks Killer Network Manager
1. Update [Intel drivers](http://www.intel.com/content/www/us/en/support/detect.html)

### Tools
1. Install [CMake](https://cmake.org/)
1. Install [Notepad++](https://notepad-plus-plus.org/)
1. Install [GitHub desktop](https://desktop.github.com/)
1. Install [pylon](https://www.baslerweb.com/en/support/downloads/software-downloads/)
1. Install [Visual Studio 2015 Community](http://softwarelicensingstore.stanford.edu/)
    1. Be sure to install C++ Tools and Windows SDK.
1. Install the latest [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk)

### Libraries

1. Download [ASIO](https://github.com/chriskohlhoff/asio) to C:\lib\asio
1. Download [SimpleINI](https://github.com/brofield/simpleini) to C:\lib\simpleini
1. Download [OpenCV 3.2](http://opencv.org/releases.html) to C:\lib\opencv
1. From this [forum post](http://ogre3d.org/forums/viewtopic.php?t=69274) install the following:
    1. [BOOST](https://goo.gl/QmGS7N) to C:\lib\boost
    1. [OGRE 1.9 SDK](https://goo.gl/jzp20i) to C:\lib\ogre

### GRBL Setup

These are instructions to program a fresh Arduino Uno board with the GRBL software.

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
