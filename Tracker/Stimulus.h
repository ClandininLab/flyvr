#pragma once

class Stimulus{
	public:
		virtual ~Stimulus(){};
		virtual void Setup() = 0;
		virtual void Update() = 0;
		virtual void Destroy() = 0;
		bool isDone = false;
};