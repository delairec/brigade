from datetime import datetime

from brigade.inbox.append_inbox_line import append_inbox_line
from brigade.inbox.inbox_locations import DISMISSED_EVENT
from brigade.inbox.read_inbox import Signal
from brigade.ledger.append_event import append_event
from brigade.ledger.inbox_dismissed import InboxDismissed
from brigade.system.paths import Paths


def dismiss_signal(paths: Paths, instant: datetime, signal: Signal) -> None:
    append_inbox_line(paths, instant, {"event": DISMISSED_EVENT, "fingerprint": signal.fingerprint})
    append_event(
        paths, instant, InboxDismissed(fingerprint=signal.fingerprint, kind=signal.kind, project=signal.project)
    )
