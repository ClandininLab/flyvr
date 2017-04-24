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
> cmake .. -G "Visual Studio 15 Win64"
> cmake --build . --target ALL_BUILD --config Release
> cd ../bin
> tracker
```

For a debug build:
```
> cmake .. -G "Visual Studio 15 Win64"
> cmake --build . --target ALL_BUILD  --config Debug
> cd ../bin
> tracker
```

## Setup

### Operating System

Install Windows 10 and update the NVidia graphics card drivers.

### Tools
1. Install [SourceTree](https://www.sourcetreeapp.com/)
1. Install [GitHub Desktop](https://desktop.github.com/)
2. Install [Visual Studio 2017 Community](https://www.visualstudio.com/)
    * Select "Desktop Development with C++" and "Game Development with C++" options
3. Install the latest version of [CMake](https://cmake.org/)
4. Install the latest version of [pylon](https://www.baslerweb.com/en/support/downloads/software-downloads/)

### Libraries

1. Download [ASIO](https://github.com/chriskohlhoff/asio), move code to C:\lib\asio
2. Download [SimpleINI](https://github.com/brofield/simpleini), move code to C:\lib\simpleini
3. Install the latest [OpenCV 2.4 binary](http://opencv.org/releases.html) to C:\lib\opencv
1. Install [.NET Framework](https://www.microsoft.com/en-us/download/details.aspx?id=21)
1. Install [DirectX SDK](http://www.microsoft.com/en-us/download/details.aspx?id=6812)

### Installing OGRE 1.9

Adapted instructions from [here](http://www.aupcgroup.com/blog/index.php?/archives/9-Building-Ogre3D-with-Microsoft-Visual-C++-14.0-Visual-Studio-Community-2015.html).

#### Ogre3D Dependencies
1. Download [OGRE dependencies code](https://bitbucket.org/cabalistic/ogredeps/downloads/) to C:\lib\ogredeps
1. Create directory C:\lib\ogredeps\build
2. Open CMake, set source directory to C:\lib\ogredeps and build directory C:\lib\ogredeps\build
3. Click Configure, wait for process to finish.  
4. Uncheck OGREDEPS_BUILD_SDL2
5. Click Configure and repeat until none of the fields are marked in red.
4. Click Generate.
5. Go to directory C:\lib\ogredeps\build, open OGREDEPS.sln
6. Set config to Release, right click ALL_BUILD and click "Build"
6. Set config to Debug, right click ALL_BUILD and click "Build"
6. Set config to Release, right click INSTALL and click "Build"
6. Set config to Debug, right click INSTALL and click "Build"

#### Ogre3D Main Library

1. Open SourceTree.
1. Click Clone / New.
1. Enter URL (https://bitbucket.org/sinbad/ogre/)[https://bitbucket.org/sinbad/ogre/]
1. Enter destination directory C:\lib\ogre
1. Click Advanced Options
1. Enter Branch v1-9
1. Click Clone.
2. Open CMake, set source directory to C:\lib\ogre and build directory C:\lib\ogre\build
3. Click Configure, wait for process to finish.  
4. Set OGRE_DEPENDENCIES_DIR to C:\lib\ogredeps\build\ogredeps
5. Uncheck OGRE_BUILD_RENDERSYSTEM_GL and  OGRE_BUILD_RENDERSYSTEM_GL3PLUS
5. Click Configure and repeat until none of the fields are marked in red.
4. Click Generate.
5. Go to directory C:\lib\ogre\build, open OGRE.sln
6. Set config to Release, right click ALL_BUILD and click "Build"
6. Set config to Debug, right click ALL_BUILD and click "Build"
6. Set config to Release, right click INSTALL and click "Build"
6. Set config to Debug, right click INSTALL and click "Build"

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

