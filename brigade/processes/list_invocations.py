from datetime import datetime
from pathlib import Path

from brigade.ledger.format_instant import format_instant
from brigade.processes.is_failed_record import is_failed_record
from brigade.processes.locate_trails import Trail, locate_trails
from brigade.processes.read_trail_records import read_trail_records


def _read_instant(trail: Trail) -> datetime:
    return trail.instant


def _describe_invocation(trail: Trail) -> dict:
    records = read_trail_records(trail.path)
    return {
        "kind": trail.kind,
        "id": trail.id,
        "instant": format_instant(trail.instant),
        "processes": len(records),
        "failed": sum(1 for record in records if is_failed_record(record)),
    }


def list_invocations(state_root: Path) -> list[dict]:
    newest_first = sorted(locate_trails(state_root), key=_read_instant, reverse=True)
    return [_describe_invocation(trail) for trail in newest_first]
