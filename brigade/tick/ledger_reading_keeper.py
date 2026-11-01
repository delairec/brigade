from collections.abc import Callable
from pathlib import Path

from brigade.ledger.read_ledger import LedgerReading, read_ledger


class LedgerReadingKeeper:
    def __init__(self, read_ledger: Callable[[Path], LedgerReading]):
        self.read_first = read_ledger
        self.reading: LedgerReading | None = None

    def read(self, state_root: Path) -> LedgerReading:
        self.reading = self.read_first(state_root) if self.reading is None else read_ledger(state_root, self.reading)
        return self.reading
