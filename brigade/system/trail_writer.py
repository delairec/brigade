import json
from collections.abc import Callable
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.create_directory import create_directory
from brigade.system.process_trace import ProcessTrace


def _append_lines(destination: Path, documents: list[dict]) -> None:
    try:
        with destination.open("a", encoding="utf-8") as trail:
            trail.writelines(f"{json.dumps(document)}\n" for document in documents)
    except OSError as error:
        raise CannotWrite(error.filename or destination, error) from error


class TrailWriter:
    def __init__(self, report: Callable[[ProcessTrace], None], mask: Callable[[str], str]):
        self._report = report
        self._mask = mask
        self._destination: Path | None = None
        self._held: list[dict] = []

    def append(self, trace: ProcessTrace) -> None:
        self._report(trace)
        document = trace.to_document(self._mask)
        if self._destination is None:
            self._held.append(document)
            return
        _append_lines(self._destination, [document])

    def locate(self, destination: Path) -> None:
        create_directory(destination.parent)
        _append_lines(destination, self._held)
        self._destination = destination
        self._held = []

    def settle(self, fallback: Path) -> None:
        if self._destination is None and self._held:
            self.locate(fallback)
