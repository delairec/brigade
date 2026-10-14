from pathlib import Path

from brigade.errors import BrigadeError
from brigade.processes.is_failed_record import is_failed_record
from brigade.processes.locate_trails import locate_trails
from brigade.processes.read_trail_records import read_trail_records

DOCUMENT_SCHEMA_VERSION = 1


def show_invocation(state_root: Path, invocation_id: str, *, failed_only: bool) -> dict:
    trail = next((trail for trail in locate_trails(state_root) if trail.id == invocation_id), None)
    if trail is None:
        raise BrigadeError(f"no run, tick or command {invocation_id}")
    records = read_trail_records(trail.path)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "kind": trail.kind,
        "id": trail.id,
        "processes": [record for record in records if is_failed_record(record)] if failed_only else records,
    }
