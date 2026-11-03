import contextlib
from collections.abc import Callable

from brigade.errors import BrigadeError

WITHHELD_MARKER = "[withheld: the PRIVATE patterns of the registered projects could not be read]"


def _withhold(text: str) -> str:
    return WITHHELD_MARKER


class StderrMasker:
    def __init__(self, read_scrubber: Callable[[], Callable[[str], str]]):
        self._read_scrubber = read_scrubber
        self._scrubber: Callable[[str], str] | None = None

    def mask(self, text: str) -> str:
        if not text:
            return text
        if self._scrubber is None:
            self._scrubber = _withhold
            with contextlib.suppress(BrigadeError):
                self._scrubber = self._read_scrubber()
        return self._scrubber(text)
