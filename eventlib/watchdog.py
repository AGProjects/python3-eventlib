"""Detect and report stalls of the eventlib hub.

Everything that runs in green threads shares the hub's OS thread (with the
twisted hub that is the twisted reactor thread). A single blocking call made
from a green thread (a synchronous socket operation, urlopen, getaddrinfo,
time.sleep, a long computation, ...) freezes all other green threads until it
returns, which is hard to diagnose after the fact.

The watchdog makes these stalls visible. The hub schedules a heartbeat every
`interval` seconds and a separate OS thread checks it. When the heartbeat is
late by more than `threshold` seconds, the stack of the hub thread (which is
the stack of the code that is blocking it) is reported, and when the hub runs
again the total duration of the stall is reported as well.

Usage, from the hub thread (for the twisted hub: the reactor thread) once the
hub is running:

    from eventlib import watchdog
    watchdog.start(threshold=1.0)

To integrate with an application logger, pass report functions:

    watchdog.start(threshold=1.0, report_stall=my_stall_logger, report_recovery=my_recovery_logger)

    report_stall(duration, stack)   # duration: seconds late so far; stack: formatted stack of the hub thread
    report_recovery(duration)       # duration: total seconds the hub did not run

The report functions are called from the watchdog thread, so they must be
thread safe (the logging module is).

Sleeping computers are not reported: when the watchdog thread notices that it
did not run for a while itself, it assumes the whole process was suspended and
restarts the measurement.
"""

import logging
import sys
import threading
import time
import traceback

from eventlib.api import get_hub


__all__ = ['start', 'stop', 'is_running']


log = logging.getLogger('eventlib.watchdog')


def _default_report_stall(duration, stack):
    log.warning('eventlib hub blocked for %.1f seconds, hub thread is at:\n%s', duration, stack)


def _default_report_recovery(duration):
    log.warning('eventlib hub was blocked for %.1f seconds', duration)


class _Watchdog(object):

    def __init__(self, threshold, interval, report_stall, report_recovery):
        self.threshold = threshold
        self.interval = interval
        self.report_stall = report_stall
        self.report_recovery = report_recovery
        self.hub = get_hub()
        self.hub_thread_id = threading.get_ident()
        self.last_beat = time.monotonic()
        self.stall_reported = False
        self.stopped = threading.Event()
        self.timer = None
        self.thread = threading.Thread(target=self._check_loop, name='eventlib-watchdog', daemon=True)

    def start(self):
        self._schedule_beat()
        self.thread.start()

    def stop(self):
        self.stopped.set()
        timer = self.timer
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    # runs in the hub thread
    def _schedule_beat(self):
        if not self.stopped.is_set():
            self.timer = self.hub.schedule_call_global(self.interval, self._beat)

    def _beat(self):
        self.last_beat = time.monotonic()
        self._schedule_beat()

    # runs in the watchdog thread
    def _check_loop(self):
        check_interval = min(self.interval, self.threshold) / 2.0
        last_check = time.monotonic()
        stall_start = None
        while not self.stopped.wait(check_interval):
            now = time.monotonic()
            if now - last_check > max(self.threshold, 5*check_interval):
                # we ourselves did not run for a while, the process (or the
                # whole computer) was suspended. Start measuring again.
                self.last_beat = now
                stall_start = None
                self.stall_reported = False
            last_check = now

            last_beat = self.last_beat
            late = now - last_beat - self.interval
            if late > self.threshold:
                if stall_start is None:
                    stall_start = last_beat + self.interval
                if not self.stall_reported:
                    self.stall_reported = True
                    self._call(self.report_stall, late, self._hub_stack())
            elif stall_start is not None:
                duration = last_beat - stall_start
                stall_start = None
                self.stall_reported = False
                self._call(self.report_recovery, duration)

    def _hub_stack(self):
        frame = sys._current_frames().get(self.hub_thread_id)
        if frame is None:
            return '  <hub thread stack not available>\n'
        return ''.join(traceback.format_stack(frame))

    @staticmethod
    def _call(function, *args):
        try:
            function(*args)
        except Exception:
            log.exception('eventlib watchdog report function failed')


_watchdog = None


def start(threshold=1.0, interval=0.25, report_stall=None, report_recovery=None):
    """Start watching the hub. Must be called from the hub thread.

    threshold: how late (in seconds) the heartbeat must be to be reported
    interval: how often (in seconds) the hub records a heartbeat
    """
    global _watchdog
    if threshold <= 0 or interval <= 0:
        raise ValueError('threshold and interval must be positive')
    stop()
    _watchdog = _Watchdog(threshold, interval, report_stall or _default_report_stall, report_recovery or _default_report_recovery)
    _watchdog.start()


def stop():
    """Stop watching the hub"""
    global _watchdog
    if _watchdog is not None:
        _watchdog.stop()
        _watchdog = None


def is_running():
    return _watchdog is not None

