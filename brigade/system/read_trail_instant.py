from datetime import UTC, datetime

from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT
from brigade.system.trail_locations import TRAIL_INSTANT_LENGTH


def read_trail_instant(name: str) -> datetime | None:
    try:
        return datetime.strptime(name[:TRAIL_INSTANT_LENGTH], COMPACT_INSTANT_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None
