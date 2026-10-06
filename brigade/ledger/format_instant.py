from datetime import UTC, datetime

INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def format_instant(instant: datetime) -> str:
    return instant.astimezone(UTC).strftime(INSTANT_FORMAT)
