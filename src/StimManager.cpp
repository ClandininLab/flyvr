// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <random>
#include <algorithm>

#include "Utility.h"
#include "StimManager.h"
#include "CylinderBars.h"

StimManager::StimManager(OgreApplication &app, 
	const std::string &stimConfigFile, 
	const std::string &GraphicsOutputFile)
	: app(app), stimConfigFile(stimConfigFile), graphicsOutputFile(GraphicsOutputFile){

	// Load the INI file
	iniFile.SetUnicode();
	iniFile.LoadFile(stimConfigFile.c_str());

	// Read the global configuration parameters
	std::string iColor(iniFile.GetValue("", "interleave-color", "0.5"));
	iColorR = getColor(iColor, ColorType::Red);
	iColorG = getColor(iColor, ColorType::Green);
	iColorB = getColor(iColor, ColorType::Blue);
	iDuration = iniFile.GetDoubleValue("", "interleave-duration", 1.0);
	randomSeed = iniFile.GetLongValue("", "random-seed", 0);

	// Read all section names
	CSimpleIniA::TNamesDepend sections;
	iniFile.GetAllSections(sections);

	// Copy section names into a vector so they can be shuffled
	stimNames = std::vector<std::string>();
	for (auto iSection = sections.begin(); iSection != sections.end(); ++iSection) {
		std::string stimName = std::string(iSection->pItem);
		if (stimName != ""){
			stimNames.push_back(stimName);
			std::cout << "Found stimulus: " << stimName << "\r\n";
		}
	}

	// Put the currentStimName pointer to the end to force a shuffle
	nextStimName = stimNames.end();

	// Create the random number generator from the provided seed
	// mt19937 is the "mersenne_twister_engine" pseudo-random number generator
	randomGenerator = std::mt19937(randomSeed);

	// Set the state to "Init" (pre-interleave)
	state = StimManagerStates::Init;

	// Open the output file stream
	outFileStream = std::ofstream(graphicsOutputFile);
	outFileStream << "managerState," << "stimName,";
	outFileStream << "flyX (m)," << "flyY (m)," << "flyZ (m),";
	outFileStream << "flyPitch (rad)," << "flyYaw (rad)," << "flyRoll (rad),";
	outFileStream << "stimString," << "timestamp (s)\n";
}

StimManager::~StimManager(){
}

// Main state machine for the stimulus manager
// Sets up the interleave background and runs each stimulus to completion
void StimManager::Update(Pose3D flyPose){
	std::string managerState;
	std::string stimString = "";
	std::string stimName = "";

	if (state == StimManagerStates::Init){
		managerState = "Init";
		app.setBackground(iColorR, iColorG, iColorB);
		lastTime = std::chrono::high_resolution_clock::now();
		state = StimManagerStates::Interleave;
	}
	else if (state == StimManagerStates::Interleave){
		managerState = "Interleave";
		auto thisTime = std::chrono::high_resolution_clock::now();
		auto duration = std::chrono::duration<double>(thisTime - lastTime).count();
		if (duration >= iDuration){
			PickNextStimulus();
			state = StimManagerStates::Stimulus;
		}
	}
	else if (state == StimManagerStates::Stimulus){
		managerState = "Stimulus";
		stimName = currentStimName;

		// Update stimulus and record stimulus state
		stimString = currentStimulus->Update(flyPose);

		// Check if stimulus is done
		if (currentStimulus->isDone){
			// If it is, tear down the scene and enter interleave
			currentStimulus.reset();
			state = StimManagerStates::Init;
		}
	}
	else{
		throw std::runtime_error("Invalid StimManager state.");
	}

	// Format output string
	std::ostringstream oss;
	oss << managerState << ",";
	oss << stimName << ",";
	oss << std::fixed << flyPose.x << ",";
	oss << std::fixed << flyPose.y << ",";
	oss << std::fixed << flyPose.z << ",";
	oss << std::fixed << flyPose.pitch << ",";
	oss << std::fixed << flyPose.yaw << ",";
	oss << std::fixed << flyPose.roll << ",";
	oss << stimString << ",";
	oss << std::fixed << GetTimeStamp();
	oss << "\n";

	// Write output string to file
	outFileStream << oss.str();
}

// Picks the next stimulus name from the configuration file
// If we've reached the end of the list, shuffle first
void StimManager::PickNextStimulus(void){
	if (nextStimName == stimNames.end()){
		// Shuffle list if we've reached the end
		ShuffleStimNames();
		nextStimName = stimNames.begin();
	}

	// Instantiate the next stimulus
	currentStimName = *nextStimName;
	MakeStimulus(currentStimName);

	// Increment the stimulus name pointer
	++nextStimName;
}

void StimManager::ShuffleStimNames(){
	std::shuffle(stimNames.begin(), stimNames.end(), randomGenerator);
}

// Creates a new stimulus object based on the specifications in the given section
void StimManager::MakeStimulus(std::string name){
	// Load the type from configuration file
	std::string type = iniFile.GetValue(name.c_str(), "type");

	// Create a new stimulus based on the specified type
	if (type == "CylinderBars"){
                currentStimulus = std::unique_ptr<CylinderBars>(new CylinderBars(name, app, iniFile));
	}
	else {
		throw std::runtime_error("Invalid stimulus type.");
	}
}
