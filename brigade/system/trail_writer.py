import json
from collections.abc import Callable
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.create_directory import create_directory
from brigade.system.process_trace import ProcessTrace


def _append_lines(destination: Path, traces: list[ProcessTrace]) -> None:
    try:
        with destination.open("a", encoding="utf-8") as trail:
            trail.writelines(f"{json.dumps(trace.to_document())}\n" for trace in traces)
    except OSError as error:
        raise CannotWrite(error.filename or destination, error) from error


class TrailWriter:
    def __init__(self, report: Callable[[ProcessTrace], None]):
        self._report = report
        self._destination: Path | None = None
        self._held: list[ProcessTrace] = []

    def append(self, trace: ProcessTrace) -> None:
        self._report(trace)
        if self._destination is None:
            self._held.append(trace)
            return
        _append_lines(self._destination, [trace])

    def locate(self, destination: Path) -> None:
        create_directory(destination.parent)
        _append_lines(destination, self._held)
        self._destination = destination
        self._held = []

    def settle(self, fallback: Path) -> None:
        if self._destination is None and self._held:
            self.locate(fallback)
