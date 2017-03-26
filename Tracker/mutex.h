#pragma once

#define LOCK(m) WaitForSingleObject(m, INFINITE)
#define UNLOCK(m) ReleaseMutex(m)