import contextlib
import os
import select
import signal
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from brigade.system.poll_until_stopped import poll_until_stopped

STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _drain(read_descriptor: int) -> None:
    with contextlib.suppress(BlockingIOError):
        os.read(read_descriptor, 512)


@dataclass(frozen=True)
class _WakeupSignals:
    signalled: list
    read_descriptor: int

    def received(self) -> bool:
        return bool(self.signalled)

    def wait(self, interval_s: float) -> None:
        select.select([self.read_descriptor], [], [], interval_s)
        _drain(self.read_descriptor)


@contextlib.contextmanager
def _receive_stop_signals() -> Iterator[_WakeupSignals]:
    signalled = []
    read_descriptor, write_descriptor = os.pipe()
    os.set_blocking(read_descriptor, False)
    os.set_blocking(write_descriptor, False)
    previous_handlers = {stop_signal: signal.getsignal(stop_signal) for stop_signal in STOP_SIGNALS}
    previous_wakeup_descriptor = signal.set_wakeup_fd(write_descriptor)
    try:
        for stop_signal in STOP_SIGNALS:
            signal.signal(stop_signal, lambda received, _frame: signalled.append(received))
        yield _WakeupSignals(signalled=signalled, read_descriptor=read_descriptor)
    finally:
        for stop_signal, handler in previous_handlers.items():
            signal.signal(stop_signal, handler)
        signal.set_wakeup_fd(previous_wakeup_descriptor)
        os.close(read_descriptor)
        os.close(write_descriptor)


def poll_until_signalled(poll: Callable[[], bool], interval_s: float) -> bool:
    with _receive_stop_signals() as signals:
        return poll_until_stopped(poll, interval_s, signals)
