# FlyVR
# http://flyvisionlab.weebly.com/
# Contact: Steven Herbst <sherbst@stanford.edu>

cmake_minimum_required(VERSION 3.6)
project (Tracker)

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
list(APPEND SOURCES "src/CylinderBars.cpp" "src/Tracker.cpp" "src/Camera.cpp")
list(APPEND SOURCES "src/OgreApplication.cpp" "src/StimManager.cpp" "src/Utility.cpp")
list(APPEND SOURCES "include/Camera.h" "include/CylinderBars.h" "include/OgreApplication.h")
list(APPEND SOURCES "include/StimManager.h" "include/Stimulus.h" "include/Stimulus.h")
list(APPEND SOURCES "include/Tracker.h" "include/Utility.h")
add_executable(tracker ${SOURCES})

# Link library files
list(APPEND PROJECT_LINK_LIBS "opencv_core2410.lib" "opencv_imgproc2410.lib")
list(APPEND PROJECT_LINK_LIBS "opencv_highgui2410.lib" "opencv_features2d2410.lib")
list(APPEND PROJECT_LINK_LIBS "OgreMain.lib" "OIS.lib" "OgreOverlay.lib")
target_link_libraries(tracker ${PROJECT_LINK_LIBS})

# Define DLL locations
set(OGRE_DLL_DIR "${OGRE_TOP}/bin/release")

# Define configuration file locations
set(BIN_DIR "${PROJECT_SOURCE_DIR}/bin")

# Define binary output file path
set(OUT_PATH $<TARGET_FILE_DIR:tracker>)

# Set up post-build copying of config files and DLLs
# http://stackoverflow.com/questions/10671916/how-to-copy-dll-files-into-the-same-folder-as-the-executable-using-cmake
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR}/OgreMain.dll")
list(APPEND POST_BUILD_COPY_LIST "${OGRE_DLL_DIR}/OgreOverlay.dll")
list(APPEND POST_BUILD_COPY_LIST "${OUT_PATH}/tracker.exe")
add_custom_command(TARGET tracker POST_BUILD       # Adds a post-build event to MyTest
    COMMAND ${CMAKE_COMMAND} -E copy_if_different  # which executes "cmake - E copy_if_different..."
        ${POST_BUILD_COPY_LIST}                    # <--this is in-file
        ${BIN_DIR})                                # <--this is out-file path
