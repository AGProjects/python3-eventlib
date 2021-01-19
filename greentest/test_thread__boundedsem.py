"""Test that BoundedSemaphore with a very high bound is as good as unbounded one"""
from eventlib import coros
from eventlib.green import thread

def allocate_lock():
    return coros.semaphore(1, 9999)

thread.allocate_lock = allocate_lock
thread.LockType = coros.BoundedSemaphore

exec(compile(open('test_thread.py').read(), 'test_thread.py', 'exec'))
