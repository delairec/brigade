def format_span(duration_ms: int) -> str:
    whole_minutes, seconds = divmod(duration_ms // 1000, 60)
    hours, minutes = divmod(whole_minutes, 60)
    if hours:
        return f"{hours} h {minutes} min" if minutes else f"{hours} h"
    if whole_minutes >= 10:
        return f"{whole_minutes} min"
    if whole_minutes:
        return f"{whole_minutes} min {seconds} s"
    return f"{seconds} s"
