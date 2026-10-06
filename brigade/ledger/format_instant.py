from datetime import datetime, timezone

INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def format_instant(instant: datetime) -> str:
    return instant.astimezone(timezone.utc).strftime(INSTANT_FORMAT)
