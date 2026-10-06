import os
import select
import signal
from collections.abc import Callable

STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _drain(read_descriptor: int) -> None:
    try:
        while os.read(read_descriptor, 512):
            pass
    except BlockingIOError:
        pass


def repeat_until_signalled(action: Callable[[], None], interval_s: float) -> int:
    signalled = []
    read_descriptor, write_descriptor = os.pipe()
    os.set_blocking(read_descriptor, False)
    os.set_blocking(write_descriptor, False)
    previous_handlers = {stop_signal: signal.getsignal(stop_signal) for stop_signal in STOP_SIGNALS}
    previous_wakeup_descriptor = signal.set_wakeup_fd(write_descriptor)
    try:
        for stop_signal in STOP_SIGNALS:
            signal.signal(stop_signal, lambda received, frame: signalled.append(received))
        repetitions = 0
        while True:
            action()
            repetitions += 1
            if signalled:
                return repetitions
            select.select([read_descriptor], [], [], interval_s)
            _drain(read_descriptor)
            if signalled:
                return repetitions
    finally:
        for stop_signal, handler in previous_handlers.items():
            signal.signal(stop_signal, handler)
        signal.set_wakeup_fd(previous_wakeup_descriptor)
        os.close(read_descriptor)
        os.close(write_descriptor)
