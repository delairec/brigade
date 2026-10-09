import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.journal_record import JOURNAL_RECORD_SHAPE, JournalRecord
from brigade.system.validate_document import DocumentInvalid, validate_document

LINE_END = b"\n"


class JournalReader:
    def __init__(self, journal_path: Path):
        self.journal_path = journal_path
        self.bytes_read = 0
        self.lines_read = 0

    def _read_record(self, number: int, line: str) -> dict:
        location = f"line {number} of {self.journal_path}"
        try:
            document = json.loads(line)
        except ValueError:
            raise BrigadeError(f"{location} is not a journal record: not a JSON document") from None
        try:
            validate_document(document, JOURNAL_RECORD_SHAPE)
        except DocumentInvalid as problem:
            raise BrigadeError(f"{location} is not a journal record: {problem}") from None
        return JournalRecord.from_document(document).to_document()

    def read_whole_records(self) -> list[dict]:
        if not self.journal_path.exists():
            return []
        with self.journal_path.open("rb") as journal:
            journal.seek(self.bytes_read)
            appended = journal.read()
        whole = appended[: appended.rfind(LINE_END) + 1]
        lines = whole.decode("utf-8").splitlines()
        records = [self._read_record(number, line) for number, line in enumerate(lines, self.lines_read + 1)]
        self.bytes_read += len(whole)
        self.lines_read += len(lines)
        return records
