import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.inbox.inbox_locations import (
    DISMISSED_EVENT,
    INBOX_DIRECTORY,
    RECORDED_EVENT,
    SIGNALS_FILE,
    SIGNALS_SCHEMA_VERSION,
)
from brigade.inbox.name_signal import name_signal
from brigade.system.instant_formats import ISO_INSTANT_FORMAT
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

NEW_STATUS = "new"
DISMISSED_STATUS = "dismissed"
DISMISSAL_SHAPE = {
    "schema_version": Field((int,), values=(SIGNALS_SCHEMA_VERSION,)),
    "ts": Field((str,)),
    "event": Field((str,), values=(RECORDED_EVENT, DISMISSED_EVENT)),
    "fingerprint": Field((str,)),
}
RECORDING_SHAPE = {
    **DISMISSAL_SHAPE,
    "kind": Field((str,)),
    "project": Field((str,), nullable=True),
    "evidence": Field((dict,)),
}
SHAPES_BY_EVENT = {RECORDED_EVENT: RECORDING_SHAPE, DISMISSED_EVENT: DISMISSAL_SHAPE}


@dataclass(frozen=True)
class Signal:
    id: str
    fingerprint: str
    kind: str
    project: str | None
    count: int
    age_s: int
    status: str
    evidence: dict


@dataclass(frozen=True)
class _Recordings:
    first: datetime
    count: int
    last: dict


def _read_instant(timestamp: str) -> datetime:
    try:
        return datetime.strptime(timestamp, ISO_INSTANT_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        raise DocumentInvalid(f"ts {timestamp!r} is not an ISO 8601 UTC instant") from None


def _read_line(path: Path, number: int, text: str) -> tuple[dict, datetime]:
    try:
        line = json.loads(text)
        validate_document(line, DISMISSAL_SHAPE)
        validate_document(line, SHAPES_BY_EVENT[line["event"]])
        instant = _read_instant(line["ts"])
    except json.JSONDecodeError:
        raise BrigadeError(f"{path}:{number}: is not JSON") from None
    except DocumentInvalid as error:
        raise BrigadeError(f"{path}:{number}: {error}") from None
    return line, instant


def _fold(recordings: _Recordings | None, line: dict, instant: datetime) -> _Recordings:
    if recordings is None:
        return _Recordings(first=instant, count=1, last=line)
    return _Recordings(first=recordings.first, count=recordings.count + 1, last=line)


def _describe(fingerprint: str, recordings: _Recordings, dismissed: set[str], now: datetime) -> Signal:
    last = recordings.last
    return Signal(
        id=name_signal(fingerprint),
        fingerprint=fingerprint,
        kind=last["kind"],
        project=last["project"],
        count=recordings.count,
        age_s=int((now - recordings.first).total_seconds()),
        status=DISMISSED_STATUS if fingerprint in dismissed else NEW_STATUS,
        evidence=last["evidence"],
    )


def read_inbox(state_root: Path, now: datetime) -> tuple[Signal, ...]:
    path = state_root / INBOX_DIRECTORY / SIGNALS_FILE
    if not path.is_file():
        return ()
    folded: dict[str, _Recordings] = {}
    dismissed: set[str] = set()
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line, instant = _read_line(path, number, text)
        fingerprint = line["fingerprint"]
        if line["event"] == DISMISSED_EVENT:
            dismissed.add(fingerprint)
        else:
            folded[fingerprint] = _fold(folded.get(fingerprint), line, instant)
    return tuple(_describe(fingerprint, recordings, dismissed, now) for fingerprint, recordings in folded.items())
