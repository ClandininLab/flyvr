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
> cmake .. -G "Visual Studio 12 Win64"
> cmake --build . --target ALL_BUILD --config Release
> cd ../bin
> tracker
```

For a debug build:
```
> cmake .. -G "Visual Studio 12 Win64"
> cmake --build . --target ALL_BUILD  --config Debug
> cd ../bin
> tracker
```

## Setup

### Operating System

Install Windows 10.

### Tools
1. Install [Visual Studio 2017 Community](https://www.visualstudio.com/)
2. Install the latest version of [CMake](https://cmake.org/)
3. Install the latest version of [pylon](https://www.baslerweb.com/en/support/downloads/software-downloads/)

### Libraries

1. Download [ASIO](https://github.com/chriskohlhoff/asio).  No compiling is necessary.
2. Download [SimpleINI](https://github.com/brofield/simpleini).  No compiling is necessary.
3. Install the [latest release](http://opencv.org/releases.html) of OpenCV from source.
4. Install [OGRE dependencies](https://bitbucket.org/cabalistic/ogredeps) from source.
5. Install [OGRE 1.9](https://bitbucket.org/sinbad/ogre/branch/v1-9) from source.

### GRBL

Adapted from instructions (here)[https://github.com/gnea/grbl/wiki/Compiling-Grbl]

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

