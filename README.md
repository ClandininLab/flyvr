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

### GRBL

Adapted from instructions [here](https://github.com/gnea/grbl/wiki/Compiling-Grbl)

1. Download GRBL source code: https://github.com/gnea/grbl
2. Open config.h
3. Change BAUD_RATE from 230400 to 400000 (around line 41)
4. Comment out existing definitions for HOMING_CYCLE_0 and HOMING_CYCLE_1 (around lines 105-106)
5. Uncomment definition for HOMING_CYCLE_0 that homes X and Y in one cycle (around line 110)
6. Save and close config.h
7. Launch the Arduino IDE
8. Click the Sketch drop-down menu, navigate to Include Library and select Add .ZIP Library.
    * IMPORTANT: Be sure to select the GRBL folder inside the grbl-XXX folder, which only contains the source files and an example directory.
9. Open the GrblUpload Arduino example.
    * Click the File down-down menu, navigate to Examples->Grbl, and select GrblUpload.
10. Compile and upload Grbl to your Arduino.
    * Connect your Arduino Uno to your computer.
    * Make sure your board is set to the Arduino Uno in the Tool->Board menu and the serial port is selected correctly in Tool->Serial Port.
    * Click the Upload, and GRBL should compile and flash to your Arduino.

