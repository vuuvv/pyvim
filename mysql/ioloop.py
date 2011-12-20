import datetime
import errno
import heapq
import os
import logging
import select
import _thread
import threading
import time
import traceback

try:
    import signal
except ImportError:
    signal = None

class _EPoll(object):
    """An epoll-based event loop using our C module for Python 2.5 systems"""
    _EPOLL_CTL_ADD = 1
    _EPOLL_CTL_DEL = 2
    _EPOLL_CTL_MOD = 3

    def __init__(self):
        self._epoll_fd = epoll.epoll_create()

    def fileno(self):
        return self._epoll_fd

    def close(self):
        os.close(self._epoll_fd)

    def register(self, fd, events):
        epoll.epoll_ctl(self._epoll_fd, self._EPOLL_CTL_ADD, fd, events)

    def modify(self, fd, events):
        epoll.epoll_ctl(self._epoll_fd, self._EPOLL_CTL_MOD, fd, events)

    def unregister(self, fd):
        epoll.epoll_ctl(self._epoll_fd, self._EPOLL_CTL_DEL, fd, 0)

    def poll(self, timeout):
        return epoll.epoll_wait(self._epoll_fd, int(timeout * 1000))


class _KQueue(object):
    """A kqueue-based event loop for BSD/Mac systems."""
    def __init__(self):
        self._kqueue = select.kqueue()
        self._active = {}

    def fileno(self):
        return self._kqueue.fileno()

    def close(self):
        self._kqueue.close()

    def register(self, fd, events):
        self._control(fd, events, select.KQ_EV_ADD)
        self._active[fd] = events

    def modify(self, fd, events):
        self.unregister(fd)
        self.register(fd, events)

    def unregister(self, fd):
        events = self._active.pop(fd)
        self._control(fd, events, select.KQ_EV_DELETE)

    def _control(self, fd, events, flags):
        kevents = []
        if events & IOLoop.WRITE:
            kevents.append(select.kevent(
                    fd, filter=select.KQ_FILTER_WRITE, flags=flags))
        if events & IOLoop.READ or not kevents:
            # Always read when there is not a write
            kevents.append(select.kevent(
                    fd, filter=select.KQ_FILTER_READ, flags=flags))
        # Even though control() takes a list, it seems to return EINVAL
        # on Mac OS X (10.6) when there is more than one event in the list.
        for kevent in kevents:
            self._kqueue.control([kevent], 0)

    def poll(self, timeout):
        kevents = self._kqueue.control(None, 1000, timeout)
        events = {}
        for kevent in kevents:
            fd = kevent.ident
            if kevent.filter == select.KQ_FILTER_READ:
                events[fd] = events.get(fd, 0) | IOLoop.READ
            if kevent.filter == select.KQ_FILTER_WRITE:
                if kevent.flags & select.KQ_EV_EOF:
                    # If an asynchronous connection is refused, kqueue
                    # returns a write event with the EOF flag set.
                    # Turn this into an error for consistency with the
                    # other IOLoop implementations.
                    # Note that for read events, EOF may be returned before
                    # all data has been consumed from the socket buffer,
                    # so we only check for EOF on write events.
                    events[fd] = IOLoop.ERROR
                else:
                    events[fd] = events.get(fd, 0) | IOLoop.WRITE
            if kevent.flags & select.KQ_EV_ERROR:
                events[fd] = events.get(fd, 0) | IOLoop.ERROR
        return events.items()


class _Select(object):
    """A simple, select()-based IOLoop implementation for non-Linux systems"""
    def __init__(self):
        self.read_fds = set()
        self.write_fds = set()
        self.error_fds = set()
        self.fd_sets = (self.read_fds, self.write_fds, self.error_fds)

    def close(self):
        pass

    def register(self, fd, events):
        if events & IOLoop.READ: self.read_fds.add(fd)
        if events & IOLoop.WRITE: self.write_fds.add(fd)
        if events & IOLoop.ERROR:
            self.error_fds.add(fd)
            # Closed connections are reported as errors by epoll and kqueue,
            # but as zero-byte reads by select, so when errors are requested
            # we need to listen for both read and error.
            self.read_fds.add(fd)

    def modify(self, fd, events):
        self.unregister(fd)
        self.register(fd, events)

    def unregister(self, fd):
        self.read_fds.discard(fd)
        self.write_fds.discard(fd)
        self.error_fds.discard(fd)

    def poll(self, timeout):
        readable, writeable, errors = select.select(
            self.read_fds, self.write_fds, self.error_fds, timeout)
        events = {}
        for fd in readable:
            events[fd] = events.get(fd, 0) | IOLoop.READ
        for fd in writeable:
            events[fd] = events.get(fd, 0) | IOLoop.WRITE
        for fd in errors:
            events[fd] = events.get(fd, 0) | IOLoop.ERROR
        return events.items()


# Choose a poll implementation. Use epoll if it is available, fall back to
# select() for non-Linux platforms
if hasattr(select, "epoll"):
    # Python 2.6+ on Linux
    _poll = select.epoll
elif hasattr(select, "kqueue"):
    # Python 2.6+ on BSD or Mac
    _poll = _KQueue
else:
    try:
        # Linux systems with our C module installed
        import epoll
        _poll = _EPoll
    except Exception:
        # All other systems
        import sys
        if "linux" in sys.platform:
            logging.warning("epoll module not found; using select()")
        _poll = _Select
