MILLISECONDS_PER_MINUTE = 60000
MINUTES_PER_HOUR = 60


def format_duration(milliseconds: int) -> str:
    hours, minutes = divmod(milliseconds // MILLISECONDS_PER_MINUTE, MINUTES_PER_HOUR)
    return f"{hours}h{minutes:02d}m"
