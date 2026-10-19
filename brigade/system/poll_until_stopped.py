from collections.abc import Callable
from typing import Protocol


class StopSignalWatcher(Protocol):
    def received(self) -> bool: ...

    def wait(self, interval_s: float) -> None: ...


def poll_until_stopped(poll: Callable[[], bool], interval_s: float, watcher: StopSignalWatcher) -> bool:
    while True:
        done = poll()
        if watcher.received():
            return True
        if done:
            return False
        watcher.wait(interval_s)
        if watcher.received():
            return True
