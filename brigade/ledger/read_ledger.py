import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from brigade.ledger.declare_event_shape import declare_event_shape
from brigade.ledger.declared_events import DECLARED_EVENTS, LEDGER_SCHEMA_VERSION, WRITTEN_SCHEMA_VERSIONS
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY
from brigade.ledger.undeclared_event import UndeclaredEvent
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

MONTH_FILE_NAME = re.compile(r"\d{4}-\d{2}\.jsonl")
UTC_SUFFIX = "Z"
LINE_END = b"\n"
NOT_JSON = "not JSON"
ENVELOPE_SHAPE = {
    "schema_version": Field((int,)),
    "ts": Field((str,)),
    "event": Field((str,)),
}


@dataclass(frozen=True)
class SkippedLine:
    file: str
    line: int
    reason: str


@dataclass(frozen=True)
class FileEnd:
    offset: int
    lines: int


START_OF_FILE = FileEnd(offset=0, lines=0)


@dataclass(frozen=True)
class LedgerReading:
    entries: tuple
    files: tuple
    skipped: tuple
    ends: dict = field(default_factory=dict, compare=False, repr=False)
    ended_entries: tuple = field(default=(), compare=False, repr=False)
    ended_skipped: tuple = field(default=(), compare=False, repr=False)


NOTHING_READ = LedgerReading(entries=(), files=(), skipped=())


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


def _check_schema_version(record: dict) -> None:
    version = WRITTEN_SCHEMA_VERSIONS.get(record["event"], LEDGER_SCHEMA_VERSION)
    validate_document(record, {"schema_version": Field((int,), values=(version,))})


def _read_event(record: dict):
    kind = DECLARED_EVENTS.get(record["event"])
    if kind is None:
        return UndeclaredEvent.from_document(record)
    validate_document(record, declare_event_shape(kind))
    return kind.from_document(record)


def _read_entry(text: str) -> LedgerEntry:
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        raise _LineRefused(NOT_JSON) from None
    try:
        validate_document(record, ENVELOPE_SHAPE)
        _check_schema_version(record)
        instant = _read_instant(record["ts"])
        event = _read_event(record)
    except DocumentInvalid as error:
        raise _LineRefused(str(error)) from None
    return LedgerEntry(instant=instant, event=event)


def _split_past_end(appended: bytes) -> tuple[int, list[str], list[str]]:
    ended_length = appended.rfind(LINE_END) + 1
    ended_lines = appended[:ended_length].decode("utf-8", errors="replace").split("\n")[:-1]
    unended_lines = [appended[ended_length:].decode("utf-8", errors="replace")] if ended_length < len(appended) else []
    return ended_length, ended_lines, unended_lines


def _list_month_files(ledger_directory: Path) -> list[Path]:
    if not ledger_directory.is_dir():
        return []
    return sorted(
        (path for path in ledger_directory.iterdir() if path.is_file() and MONTH_FILE_NAME.fullmatch(path.name)),
        key=lambda path: path.name,
    )


def _read_past(path: Path, end: FileEnd) -> bytes:
    with path.open("rb") as month_file:
        month_file.seek(end.offset)
        return month_file.read()


def _read_lines(lines: list[str], path: Path, first_number: int) -> tuple[list, list]:
    entries = []
    skipped = []
    for number, text in enumerate(lines, start=first_number):
        try:
            entries.append(_read_entry(text))
        except _LineRefused as refusal:
            skipped.append(SkippedLine(file=str(path), line=number, reason=str(refusal)))
    return entries, skipped


def read_ledger(state_root: Path, since: LedgerReading = NOTHING_READ) -> LedgerReading:
    paths = _list_month_files(state_root / LEDGER_DIRECTORY)
    ended_entries = list(since.ended_entries)
    ended_skipped = list(since.ended_skipped)
    entries = list(ended_entries)
    skipped = list(ended_skipped)
    ends = dict(since.ends)
    for path in paths:
        end = ends.get(str(path), START_OF_FILE)
        appended = _read_past(path, end)
        ended_length, ended_lines, unended_lines = _split_past_end(appended)
        read_entries, read_skipped = _read_lines(ended_lines, path, end.lines + 1)
        ended_entries.extend(read_entries)
        ended_skipped.extend(read_skipped)
        entries.extend(read_entries)
        skipped.extend(read_skipped)
        unended_entries, unended_skipped = _read_lines(unended_lines, path, end.lines + len(ended_lines) + 1)
        entries.extend(unended_entries)
        skipped.extend(unended_skipped)
        ends[str(path)] = FileEnd(offset=end.offset + ended_length, lines=end.lines + len(ended_lines))
    return LedgerReading(
        entries=tuple(entries),
        files=tuple(str(path) for path in paths),
        skipped=tuple(skipped),
        ends=ends,
        ended_entries=tuple(ended_entries),
        ended_skipped=tuple(ended_skipped),
    )
