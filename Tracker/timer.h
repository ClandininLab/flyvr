#pragma once

#define TIMER_SCALE_FACTOR (100e-9)

// Returns the time since Jan 1, 1601
// Increment is 100ns
__int64 GetTimeStamp();