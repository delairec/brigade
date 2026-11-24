from datetime import UTC, datetime

SHORT_INSTANT_FORMAT = "%Y-%m-%d %H:%MZ"


def format_short_instant(at: str) -> str:
    return datetime.fromisoformat(at).astimezone(UTC).strftime(SHORT_INSTANT_FORMAT)
