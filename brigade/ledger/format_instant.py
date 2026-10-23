from datetime import UTC, datetime

from brigade.system.instant_formats import ISO_INSTANT_FORMAT


def format_instant(instant: datetime) -> str:
    return instant.astimezone(UTC).strftime(ISO_INSTANT_FORMAT)
