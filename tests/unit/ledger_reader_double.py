from pathlib import Path

from brigade.ledger.read_ledger import LedgerReading, read_ledger


class LedgerReaderDouble:
    def __init__(self):
        self.state_roots = []

    def read(self, state_root: Path) -> LedgerReading:
        self.state_roots.append(state_root)
        return read_ledger(state_root)
