import sys
from datetime import UTC, datetime
from pathlib import Path

from brigade.system.instant_formats import ISO_INSTANT_FORMAT


def describe_stop_hook(entry_point: Path, stop_at: str | None) -> tuple[str, ...] | None:
    if stop_at is None:
        return None
    epoch = round(datetime.strptime(stop_at, ISO_INSTANT_FORMAT).replace(tzinfo=UTC).timestamp())
    return (sys.executable, str(entry_point), "run", "stop-hook", "--at", str(epoch))
