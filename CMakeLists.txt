cmake_minimum_required(VERSION 3.1.0)
project (Tracker)

# Use C++11
set(CMAKE_CXX_STANDARD 11) # C++11...
set(CMAKE_CXX_STANDARD_REQUIRED ON) #...is required...
set(CMAKE_CXX_EXTENSIONS OFF) #...without compiler extensions like gnu++11

# Bring in headers
include_directories(include "/Users/sgherbst/Documents/Stanford/Fly VR/simpleini" "/Users/sgherbst/Documents/OgreSDK/include/OGRE" "/Users/sgherbst/Documents/OgreSDK/include/OGRE/Overlay" "/Users/sgherbst/Documents/OgreSDK/include/OIS")

# Define all source files
set(SOURCES "src/CylinderBars.cpp" "src/Tracker.cpp" "src/Camera.cpp" "src/OgreApplication.cpp" "src/StimManager.cpp" "src/Utility.cpp")

#For the static library:
#set ( PROJECT_LINK_LIBS libtestStudent.a )
#link_directories( ~/exploringBB/extras/cmake/studentlib_static/build )
 
add_executable(tracker ${SOURCES})
#target_link_libraries(libtest ${PROJECT_LINK_LIBS} )
