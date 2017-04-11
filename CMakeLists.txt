# FlyVR
# http://flyvisionlab.weebly.com/
# Contact: Steven Herbst <sherbst@stanford.edu>

cmake_minimum_required(VERSION 3.6)
project (Tracker)

# Use C++11
set(CMAKE_CXX_STANDARD 11) # C++11...
set(CMAKE_CXX_STANDARD_REQUIRED ON) #...is required...
set(CMAKE_CXX_EXTENSIONS OFF) #...without compiler extensions like gnu++11

# Library locations
set(INI_TOP "C:/lib/simpleini-master")
set(CV_TOP "C:/lib/opencv/build")
set(OGRE_TOP "C:/lib/sinbad-ogre-108ab0bcc696/build/sdk")

# Bring in headers
set(INI_INC_DIR ${INI_TOP})
set(CV_INC_DIR "${CV_TOP}/include")
set(OGRE_INC_DIR "${OGRE_TOP}/include")
include_directories(include ${INI_INC_DIR} ${CV_INC_DIR} "${OGRE_INC_DIR}/OGRE" "${OGRE_INC_DIR}/OGRE/Overlay" "${OGRE_INC_DIR}/OIS")

# Bring in library directories
set(CV_LIB_DIR "${CV_TOP}/x64/vc12/lib")
set(OGRE_LIB_DIR "${OGRE_TOP}/lib/release")
link_directories(${CV_LIB_DIR} ${OGRE_LIB_DIR})

# Define all source files
set(SOURCES "src/CylinderBars.cpp" "src/Tracker.cpp" "src/Camera.cpp" "src/OgreApplication.cpp" "src/StimManager.cpp" "src/Utility.cpp")
add_executable(tracker ${SOURCES})

# Link library files
set(PROJECT_LINK_LIBS "opencv_core2410.lib" "opencv_imgproc2410.lib" "opencv_highgui2410.lib" "opencv_features2d2410.lib" "OgreMain.lib" "OIS.lib" "OgreOverlay.lib")
target_link_libraries(tracker ${PROJECT_LINK_LIBS})


