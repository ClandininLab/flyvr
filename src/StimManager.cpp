// FlyVR
// http://flyvisionlab.weebly.com/
// Contact: Steven Herbst <sherbst@stanford.edu>

#include <chrono>
#include <random>
#include <algorithm>

#include "Utility.h"
#include "StimManager.h"
#include "CylinderBars.h"

// Name of the stimulus configuration file
// TODO: determine this automatically
auto ConfigFileName = "C:\\dev\\Tracker\\Tracker\\config.ini";

StimManager::StimManager(OgreApplication &app)
	: app(app){

	// Load the INI file
	iniFile.SetUnicode();
	iniFile.LoadFile(ConfigFileName);

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

	// Put the stim name pointer to the end to force a shuffle
	currentStimName = stimNames.end();

	// Create the random number generator from the provided seed
	// mt19937 is the "mersenne_twister_engine" pseudo-random number generator
	randomGenerator = std::mt19937(randomSeed);

	// Set the state to "Init" (pre-interleave)
	state = StimManagerStates::Init;
}

StimManager::~StimManager(){
}

// Main state machine for the stimulus manager
// Sets up the interleave background and runs each stimulus to completion
void StimManager::Update(void){
	if (state == StimManagerStates::Init){
		app.setBackground(iColorR, iColorG, iColorB);
		lastTime = std::chrono::high_resolution_clock::now();
		state = StimManagerStates::Interleave;
	}
	else if (state == StimManagerStates::Interleave){
		auto thisTime = std::chrono::high_resolution_clock::now();
		auto duration = std::chrono::duration<double>(thisTime - lastTime).count();
		if (duration >= iDuration){
			PickNextStimulus();
			state = StimManagerStates::Stimulus;
		}
	}
	else if (state == StimManagerStates::Stimulus){
		// Update stimulus
		currentStimulus->Update();

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
}

// Picks the next stimulus name from the configuration file
// If we've reached the end of the list, shuffle first
void StimManager::PickNextStimulus(void){
	// Shuffle list if we've reached the end
	if (currentStimName == stimNames.end()){
		std::shuffle(stimNames.begin(), stimNames.end(), randomGenerator);
		currentStimName = stimNames.begin();
	}

	// Instantiate the next stimulus
	MakeStimulus(*currentStimName);

	// increment the pointer
	currentStimName++;
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
