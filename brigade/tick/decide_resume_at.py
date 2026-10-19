from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from brigade.system.reset_hour import ResetHour

WAIT_WITHOUT_RESET = timedelta(minutes=30)
ONE_DAY = timedelta(days=1)
HOUR_SEPARATOR = ":"


def decide_resume_at(now: datetime, reset: ResetHour | None) -> datetime:
    if reset is None:
        return now + WAIT_WITHOUT_RESET
    clock = now if reset.timezone is None else now.astimezone(ZoneInfo(reset.timezone))
    hour, minute = (int(part) for part in reset.hour.split(HOUR_SEPARATOR))
    reset_today = clock.replace(hour=hour, minute=minute, second=0, microsecond=0)
    resume_at = reset_today if reset_today > clock else reset_today + ONE_DAY
    return resume_at.astimezone(UTC)
