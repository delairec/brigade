import contextlib
import os
import select
import signal
from collections.abc import Callable

STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _drain(read_descriptor: int) -> None:
    with contextlib.suppress(BlockingIOError):
        os.read(read_descriptor, 512)


def poll_until_signalled(poll: Callable[[], bool], interval_s: float) -> bool:
    signalled = []
    read_descriptor, write_descriptor = os.pipe()
    os.set_blocking(read_descriptor, False)
    os.set_blocking(write_descriptor, False)
    previous_handlers = {stop_signal: signal.getsignal(stop_signal) for stop_signal in STOP_SIGNALS}
    previous_wakeup_descriptor = signal.set_wakeup_fd(write_descriptor)
    try:
        for stop_signal in STOP_SIGNALS:
            signal.signal(stop_signal, lambda received, _frame: signalled.append(received))
        while True:
            done = poll()
            if signalled:
                return True
            if done:
                return False
            select.select([read_descriptor], [], [], interval_s)
            _drain(read_descriptor)
            if signalled:
                return True
    finally:
        for stop_signal, handler in previous_handlers.items():
            signal.signal(stop_signal, handler)
        signal.set_wakeup_fd(previous_wakeup_descriptor)
        os.close(read_descriptor)
        os.close(write_descriptor)
