import tomllib
from datetime import datetime, timedelta
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.paths import Paths
from brigade.system.read_trail_days import read_trail_days
from brigade.system.read_trail_instant import read_trail_instant
from brigade.system.trail_locations import (
    COMMANDS_DIRECTORY,
    TICKS_DIRECTORY,
    TRAIL_SUFFIX,
)


def _read_configuration_document(configuration: Path) -> dict | None:
    try:
        return tomllib.loads(configuration.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _list_trails(state_root: Path) -> list[Path]:
    return [
        trail
        for directory in (TICKS_DIRECTORY, COMMANDS_DIRECTORY)
        if (state_root / directory).is_dir()
        for trail in (state_root / directory).glob(f"*{TRAIL_SUFFIX}")
    ]


def remove_expired_trails(paths: Paths, now: datetime) -> None:
    configuration = paths.configuration_file
    document = _read_configuration_document(configuration)
    if document is None:
        return
    try:
        trail_days = read_trail_days(document, configuration)
    except BrigadeError:
        return
    oldest_kept = now - timedelta(days=trail_days)
    for trail in _list_trails(paths.state_root):
        instant = read_trail_instant(trail.name)
        if instant is not None and instant < oldest_kept:
            trail.unlink(missing_ok=True)
