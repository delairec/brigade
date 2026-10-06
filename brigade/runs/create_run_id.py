import secrets
from datetime import datetime, timezone

RUN_INSTANT_FORMAT = "%Y%m%dT%H%M%SZ"
SUFFIX_BYTES = 3


def create_run_id(now: datetime) -> str:
    return f"{now.astimezone(timezone.utc).strftime(RUN_INSTANT_FORMAT)}-{secrets.token_hex(SUFFIX_BYTES)}"
