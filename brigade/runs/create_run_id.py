import secrets
from datetime import UTC, datetime

from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT

SUFFIX_BYTES = 3


def create_run_id(now: datetime) -> str:
    return f"{now.astimezone(UTC).strftime(COMPACT_INSTANT_FORMAT)}-{secrets.token_hex(SUFFIX_BYTES)}"
