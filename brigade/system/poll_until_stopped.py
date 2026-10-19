from collections.abc import Callable
from typing import Protocol


class StopSignals(Protocol):
    def received(self) -> bool: ...

    def wait(self, interval_s: float) -> None: ...


def poll_until_stopped(poll: Callable[[], bool], interval_s: float, signals: StopSignals) -> bool:
    while True:
        done = poll()
        if signals.received():
            return True
        if done:
            return False
        signals.wait(interval_s)
        if signals.received():
            return True
