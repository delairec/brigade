from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from brigade.runs.run_locations import PROCESSES_FILE, RUNS_DIRECTORY
from brigade.system.read_trail_instant import read_trail_instant
from brigade.system.trail_locations import (
    COMMANDS_DIRECTORY,
    TICKS_DIRECTORY,
    TRAIL_SUFFIX,
)

RUN_KIND = "run"
SETTLED_TRAIL_KINDS = (("tick", TICKS_DIRECTORY), ("command", COMMANDS_DIRECTORY))


@dataclass(frozen=True)
class Trail:
    kind: str
    id: str
    instant: datetime
    path: Path


def _describe_trail(kind: str, trail_id: str, path: Path) -> Trail | None:
    instant = read_trail_instant(trail_id)
    if instant is None:
        return None
    return Trail(kind=kind, id=trail_id, instant=instant, path=path)


def locate_trails(state_root: Path) -> list[Trail]:
    run_trails = [
        _describe_trail(RUN_KIND, path.parent.name, path)
        for path in (state_root / RUNS_DIRECTORY).glob(f"*/{PROCESSES_FILE}")
    ]
    settled_trails = [
        _describe_trail(kind, path.name.removesuffix(TRAIL_SUFFIX), path)
        for kind, directory in SETTLED_TRAIL_KINDS
        for path in (state_root / directory).glob(f"*{TRAIL_SUFFIX}")
    ]
    return [trail for trail in (*run_trails, *settled_trails) if trail is not None]
