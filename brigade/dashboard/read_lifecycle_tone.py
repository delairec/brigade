NEUTRAL_TONE = "faint"
LIFECYCLE_TONES = {
    "open": "you",
    "todo": "work",
    "active": "work",
    "implemented": "done",
    "reached": "done",
    "closed": "done",
    "archived": "off",
    "rejected": "off",
}


def read_lifecycle_tone(status: str | None) -> str:
    return LIFECYCLE_TONES.get(status, NEUTRAL_TONE)
