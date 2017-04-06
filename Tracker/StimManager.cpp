#include "stdafx.h"

#include <chrono>
#include <random>
#include <algorithm>
#include "StimManager.h"
#include "CylinderBars.h"

StimManager::StimManager(OgreApplication &app) 
	: app(app){

	// Load the INI file
	iniFile.SetUnicode();
	iniFile.LoadFile(CONFIG_FILE_NAME);

	// Read the global configuration parameters
	// TODO: allow for RGB hex specific of interleave color
	iColorR = iniFile.GetDoubleValue("", "interleave-color");
	iColorG = iniFile.GetDoubleValue("", "interleave-color");
	iColorB = iniFile.GetDoubleValue("", "interleave-color");
	iDuration = iniFile.GetDoubleValue("", "interleave-duration");
	randomSeed = iniFile.GetLongValue("", "random-seed");

	// Read all section names
	CSimpleIniA::TNamesDepend sections;
	iniFile.GetAllSections(sections);

	// Copy section names into a vector so they can be shuffled
	stimNames = std::vector<std::string>();
	for (auto iSection=sections.begin(); iSection != sections.end(); ++iSection) {
		std::string stimName = std::string(iSection->pItem);
		if (stimName != ""){
			stimNames.push_back(stimName);
			std::cout << "Found section: " << stimName << "\n";
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
			currentStimulus->Setup();
			state = StimManagerStates::Stimulus;
		}
	}
	else if (state == StimManagerStates::Stimulus){
		// Update stimulus
		currentStimulus->Update();

		// Check if stimulus is done
		if (currentStimulus->isDone){
			// If it is, tear down the scene and enter interleave
			currentStimulus->Destroy();
			state = StimManagerStates::Init;
		}
	}
	else{
		throw std::exception("Invalid StimManager state.");
	}
}

void StimManager::PickNextStimulus(void){
	if (currentStimName == stimNames.end()){
		// Shuffle list if we've reached the end
		std::shuffle(stimNames.begin(), stimNames.end(), randomGenerator);
		currentStimName = stimNames.begin();
	}

	// instantiate the next stimulus
	MakeNextStimulus(*currentStimName);

	// increment the pointer
	currentStimName++;
}

void StimManager::MakeNextStimulus(std::string name){
	// Load the type from configuration file
	std::string type = iniFile.GetValue(name.c_str(), "type");

	if (type == "CylinderBars"){
		currentStimulus = std::make_unique<CylinderBars>(name, app, iniFile);
	}
	else {
		throw std::exception("Invalid stimulus type.");
	}
}