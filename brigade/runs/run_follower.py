from collections.abc import Callable
from pathlib import Path

from brigade.runs.journal_reader import JournalReader
from brigade.runs.run_locations import JOURNAL_FILE


class RunFollower:
    def __init__(self, run_directory: Path, describe: Callable[[Path], dict]):
        self.run_directory = run_directory
        self.describe = describe
        self.journal_reader = JournalReader(run_directory / JOURNAL_FILE)
        self.run = None

    def read_records(self) -> list[dict]:
        self.run = self.describe(self.run_directory)
        return self.journal_reader.read_whole_records()
