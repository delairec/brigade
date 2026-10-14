MS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60


def format_duration(duration_ms: int) -> str:
    minutes, seconds = divmod(duration_ms // MS_PER_SECOND, SECONDS_PER_MINUTE)
    return f"{minutes}m{seconds:02d}s"
