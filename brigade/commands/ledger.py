from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Union

from brigade.ledger.describe_overview import describe_overview
from brigade.ledger.describe_project import describe_project
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.read_ledger import read_ledger

DOCUMENT_SCHEMA_VERSION = 1


def _resolve_since(since: Union[None, timedelta, date], now: datetime) -> Optional[datetime]:
    if since is None:
        return None
    if isinstance(since, timedelta):
        return now - since
    return datetime.combine(since, time(), tzinfo=timezone.utc)


def ledger(request, runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    if request.wave is not None:
        view = describe_wave(reading, request.wave)
    elif request.project is not None:
        view = describe_project(reading, request.project, _resolve_since(request.since, runtime.now))
    else:
        view = describe_overview(reading)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **view, "skipped": [asdict(line) for line in reading.skipped]}
