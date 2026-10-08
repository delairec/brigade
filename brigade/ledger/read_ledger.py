import json
import re
from dataclasses import MISSING, dataclass, fields
from datetime import datetime
from pathlib import Path

from brigade.ledger.declared_events import DECLARED_EVENTS, LEDGER_SCHEMA_VERSION
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY
from brigade.ledger.undeclared_event import UndeclaredEvent
from brigade.system.validate_document import KIND_NAMES, DocumentInvalid, Field, validate_document

MONTH_FILE_NAME = re.compile(r"\d{4}-\d{2}\.jsonl")
UTC_SUFFIX = "Z"
NOT_JSON = "not JSON"
ENVELOPE_SHAPE = {
    "schema_version": Field((int,), values=(LEDGER_SCHEMA_VERSION,)),
    "ts": Field((str,)),
    "event": Field((str,)),
}
DECLARED_FIELD = Field(tuple(KIND_NAMES), nullable=True)


@dataclass(frozen=True)
class SkippedLine:
    file: str
    line: int
    reason: str


@dataclass(frozen=True)
class LedgerReading:
    entries: tuple
    files: tuple
    skipped: tuple


class _LineRefused(Exception):
    pass


def _read_instant(timestamp: str) -> datetime:
    refusal = _LineRefused(f"ts {timestamp!r} is not an ISO 8601 UTC instant")
    if not timestamp.endswith(UTC_SUFFIX):
        raise refusal
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        raise refusal from None


def _read_event(record: dict):
    kind = DECLARED_EVENTS.get(record["event"])
    if kind is None:
        return UndeclaredEvent.from_document(record)
    validate_document(record, {field.name: DECLARED_FIELD for field in fields(kind) if field.default is MISSING})
    return kind.from_document(record)


def _read_entry(text: str) -> LedgerEntry:
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        raise _LineRefused(NOT_JSON) from None
    try:
        validate_document(record, ENVELOPE_SHAPE)
        instant = _read_instant(record["ts"])
        event = _read_event(record)
    except DocumentInvalid as error:
        raise _LineRefused(str(error)) from None
    return LedgerEntry(instant=instant, event=event)


def _split_lines(content: str) -> list[str]:
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def _list_month_files(ledger_directory: Path) -> list[Path]:
    if not ledger_directory.is_dir():
        return []
    return sorted(
        (path for path in ledger_directory.iterdir() if path.is_file() and MONTH_FILE_NAME.fullmatch(path.name)),
        key=lambda path: path.name,
    )


def read_ledger(state_root: Path) -> LedgerReading:
    paths = _list_month_files(state_root / LEDGER_DIRECTORY)
    entries = []
    skipped = []
    for path in paths:
        content = path.read_bytes().decode("utf-8", errors="replace")
        for number, text in enumerate(_split_lines(content), start=1):
            try:
                entries.append(_read_entry(text))
            except _LineRefused as refusal:
                skipped.append(SkippedLine(file=str(path), line=number, reason=str(refusal)))
    return LedgerReading(entries=tuple(entries), files=tuple(str(path) for path in paths), skipped=tuple(skipped))
