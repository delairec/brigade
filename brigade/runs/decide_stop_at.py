from datetime import datetime, timedelta

from brigade.system.instant_formats import ISO_INSTANT_FORMAT


def decide_stop_at(launched_at: datetime, wall_limit_s: float, margin_s: float) -> str | None:
    if wall_limit_s <= margin_s:
        return None
    return (launched_at + timedelta(seconds=wall_limit_s - margin_s)).strftime(ISO_INSTANT_FORMAT)
