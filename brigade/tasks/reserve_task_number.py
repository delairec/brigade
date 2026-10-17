import json
from pathlib import Path

from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths
from brigade.system.write_json_atomically import write_json_atomically

DOCUMENT_SCHEMA_VERSION = 1
RESERVATIONS_DIRECTORY = "reservations"
RESERVATIONS_SUFFIX = ".json"
LOCK_PREFIX = "reservations-"
LOCK_SUFFIX = ".lock"
NOTHING_RESERVED = 0


def _read_reserved(reservations: Path) -> list[int]:
    if not reservations.exists():
        return []
    return json.loads(reservations.read_text(encoding="utf-8"))["task_numbers"]


def reserve_task_number(paths: Paths, project: str, next_corpus_number: int) -> int:
    reservations = paths.state_root / RESERVATIONS_DIRECTORY / f"{project}{RESERVATIONS_SUFFIX}"
    with hold_lock(paths.lock_directory / f"{LOCK_PREFIX}{project}{LOCK_SUFFIX}"):
        reserved = _read_reserved(reservations)
        number = max(next_corpus_number, max(reserved, default=NOTHING_RESERVED) + 1)
        write_json_atomically(
            reservations, {"schema_version": DOCUMENT_SCHEMA_VERSION, "task_numbers": [*reserved, number]}
        )
    return number
