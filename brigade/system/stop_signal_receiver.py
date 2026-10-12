import contextlib
import signal
from collections.abc import Iterator
from typing import Self

STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


class StopRequested(BaseException):
    pass


class StopSignalReceiver:
    def __init__(self):
        self.requested = False
        self._raising = False
        self._previous_handlers = {}

    def __enter__(self) -> Self:
        for stop_signal in STOP_SIGNALS:
            self._previous_handlers[stop_signal] = signal.signal(stop_signal, self._receive)
        return self

    def __exit__(self, *_exception) -> None:
        for stop_signal, handler in self._previous_handlers.items():
            signal.signal(stop_signal, handler)

    @contextlib.contextmanager
    def raising(self) -> Iterator[None]:
        self._raising = True
        try:
            if self.requested:
                raise StopRequested
            yield
        finally:
            self._raising = False

    @contextlib.contextmanager
    def holding(self) -> Iterator[None]:
        raising = self._raising
        self._raising = False
        try:
            yield
        finally:
            self._raising = raising
        if self._raising and self.requested:
            self._raising = False
            raise StopRequested

    def _receive(self, _received: int, _frame) -> None:
        self.requested = True
        if self._raising:
            self._raising = False
            raise StopRequested
