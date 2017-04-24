# FlyVR
# http://flyvisionlab.weebly.com/
# Contact: Steven Herbst <sherbst@stanford.edu>

cmake_minimum_required(VERSION 3.6)
project (Tracker)

# Library locations
set(INI_TOP "C:/lib/simpleini")
set(CV_TOP "C:/lib/opencv/build")
set(OGRE_TOP "C:/lib/ogre/build/sdk")
set(ASIO_TOP "C:/lib/asio")

# Bring in headers
set(INI_INC_DIR ${INI_TOP})
set(CV_INC_DIR "${CV_TOP}/include")
set(ASIO_INC_DIR "${ASIO_TOP}/include")
set(OGRE_INC_DIR "${OGRE_TOP}/include")
list(APPEND INCLUDE_DIRS ${INI_INC_DIR} ${CV_INC_DIR} ${ASIO_INC_DIR})
list(APPEND INCLUDE_DIRS "${OGRE_INC_DIR}/OGRE" "${OGRE_INC_DIR}/OGRE/Overlay" "${OGRE_INC_DIR}/OIS")
include_directories(include ${INCLUDE_DIRS})

# Bring in library directories
# Note that CMake will add Release and Debug subdirectories for each link_directory
set(CV_LIB_DIR "${CV_TOP}/x64/vc12/lib")
set(OGRE_LIB_DIR "${OGRE_TOP}/lib")
link_directories(${CV_LIB_DIR} ${OGRE_LIB_DIR})

# Define all source files
list(APPEND SOURCES "src/CylinderBars.cpp" "src/Tracker.cpp" "src/Camera.cpp")
list(APPEND SOURCES "src/OgreApplication.cpp" "src/StimManager.cpp" "src/Utility.cpp")
list(APPEND SOURCES "src/Arduino.cpp" "src/Serial.cpp")
list(APPEND SOURCES "include/Camera.h" "include/CylinderBars.h" "include/OgreApplication.h")
list(APPEND SOURCES "include/StimManager.h" "include/Stimulus.h" "include/Stimulus.h")
list(APPEND SOURCES "include/Tracker.h" "include/Utility.h" "include/Arduino.h" "include/Serial.h")
add_executable(tracker ${SOURCES})

# Set up linking
target_link_libraries(tracker 
            debug opencv_core2413d.lib optimized opencv_core2413.lib
            debug opencv_imgproc2413d.lib optimized opencv_imgproc2413.lib
            debug opencv_highgui2413d.lib optimized opencv_highgui2413.lib
            debug opencv_features2d2413d.lib optimized opencv_features2d2413.lib
            debug OgreMain_d.lib optimized OgreMain.lib
            debug OIS_d.lib optimized OIS.lib
            debug OgreOverlay_d.lib optimized OgreOverlay.lib)

# Define DLL locations
set(OGRE_DLL_DIR_OPTIMIZED "${OGRE_TOP}/bin/release")
set(OGRE_DLL_DIR_DEBUG "${OGRE_TOP}/bin/debug")

# Define configuration file locations
set(BIN_DIR "${PROJECT_SOURCE_DIR}/bin")

# Define binary output file path
set(OUT_PATH $<TARGET_FILE_DIR:tracker>)

# Set up post-build copying of config files and DLLs
# http://stackoverflow.com/questions/10671916/how-to-copy-dll-files-into-the-same-folder-as-the-executable-using-cmake
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR_OPTIMIZED}/OgreMain.dll")
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR_OPTIMIZED}/OgreOverlay.dll")
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR_DEBUG}/OgreMain_d.dll")
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR_DEBUG}/OgreOverlay_d.dll")
list(APPEND POST_BUILD_COPY_LIST "${OUT_PATH}/tracker.exe")
add_custom_command(TARGET tracker POST_BUILD       # Adds a post-build event to MyTest
    COMMAND ${CMAKE_COMMAND} -E copy_if_different  # which executes "cmake - E copy_if_different..."
        ${POST_BUILD_COPY_LIST}                    # <--this is in-file
        ${BIN_DIR})                                # <--this is out-file path

# Pass in the location of OGRE SDK
add_definitions(-DOGRE_TOP="${OGRE_TOP}")

# Use ASIO without Boost
add_definitions(-DASIO_STANDALONE)
add_definitions(-DWIN32_LEAN_AND_MEAN)

# Need to define _WIN32_WINNT for ASIO
# http://stackoverflow.com/questions/9742003/platform-detection-in-cmake
macro(get_WIN32_WINNT version)
    if (WIN32 AND CMAKE_SYSTEM_VERSION)
        set(ver ${CMAKE_SYSTEM_VERSION})
        string(REPLACE "." "" ver ${ver})
        string(REGEX REPLACE "([0-9])" "0\\1" ver ${ver})

        set(${version} "0x${ver}")
    endif()
endmacro()

get_WIN32_WINNT(ver)
add_definitions(-D_WIN32_WINNT=${ver})