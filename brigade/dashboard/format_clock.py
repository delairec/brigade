from datetime import UTC, datetime


def format_clock(at: str) -> str:
    return datetime.fromisoformat(at).astimezone(UTC).strftime("%H:%M:%SZ")
