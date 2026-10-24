from dataclasses import dataclass
from datetime import datetime

from brigade.inbox.append_inbox_line import append_inbox_line
from brigade.inbox.inbox_locations import RECORDED_EVENT
from brigade.ledger.append_event import append_event
from brigade.ledger.inbox_recorded import InboxRecorded
from brigade.system.paths import Paths


@dataclass(frozen=True)
class NewSignal:
    kind: str
    project: str | None
    fingerprint: str
    evidence: dict


def record_signal(paths: Paths, instant: datetime, signal: NewSignal) -> None:
    append_inbox_line(
        paths,
        instant,
        {
            "event": RECORDED_EVENT,
            "kind": signal.kind,
            "project": signal.project,
            "fingerprint": signal.fingerprint,
            "evidence": signal.evidence,
        },
    )
    append_event(
        paths, instant, InboxRecorded(fingerprint=signal.fingerprint, kind=signal.kind, project=signal.project)
    )
