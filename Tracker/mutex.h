#ifndef MUTEX_H
#define MUTEX_H

#define LOCK(m) WaitForSingleObject(m, INFINITE)
#define UNLOCK(m) ReleaseMutex(m)

#endif