from datetime import datetime

from brigade.errors import BrigadeError
from brigade.ledger.declared_events import RUN_FINISHED
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import LedgerEntry, LedgerReading
from brigade.ledger.summarize_steps import summarize_steps

FIRST_HAND_OVER_SEGMENT = 2
MILLISECONDS_PER_SECOND = 1000


def _measure_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * MILLISECONDS_PER_SECOND)


def _list_tasks(records: list[dict]) -> list[str]:
    return list(dict.fromkeys(record["task"] for record in records if record.get("task") is not None))


def _summarize_by(runs: list[dict], key: str) -> dict:
    names = sorted({run[key] for run in runs}, key=str)
    return {name: summarize_steps(run["steps"] for run in runs if run[key] == name) for name in names}


def _pair_pauses(entries: list[LedgerEntry]) -> list[dict]:
    pauses = []
    paused_at = None
    for entry in entries:
        event = entry.record["event"]
        if event == "wave.paused" and paused_at is None:
            paused_at = entry.instant
        elif event == "wave.resumed" and paused_at is not None:
            pauses.append(
                {
                    "paused_at": format_instant(paused_at),
                    "resumed_at": format_instant(entry.instant),
                    "duration_ms": _measure_ms(paused_at, entry.instant),
                }
            )
            paused_at = None
    if paused_at is not None:
        pauses.append({"paused_at": format_instant(paused_at), "resumed_at": None, "duration_ms": None})
    return pauses


def describe_wave(reading: LedgerReading, wave: str) -> dict:
    entries = [entry for entry in reading.entries if entry.record.get("wave") == wave]
    if not entries:
        raise BrigadeError(f"no event names the wave {wave}")
    records = [entry.record for entry in entries]
    first = min(entry.instant for entry in entries)
    last = max(entry.instant for entry in entries)
    runs = [record for record in records if record["event"] == RUN_FINISHED]
    pauses = _pair_pauses(entries)
    return {
        "view": "wave",
        "wave": wave,
        "first": format_instant(first),
        "last": format_instant(last),
        "wall_time_ms": _measure_ms(first, last),
        "tasks": _list_tasks(records),
        "pull_requests": [
            {"task": record["task"], "pr": record["pr"], "rounds": record["rounds"]}
            for record in records
            if record["event"] == "pr.merged"
        ],
        "steps": {"by_slot": _summarize_by(runs, "slot"), "by_role": _summarize_by(runs, "role")},
        "pauses": pauses,
        "paused_ms": sum(pause["duration_ms"] for pause in pauses if pause["duration_ms"] is not None),
        "hand_overs": [
            {"task": run["task"], "role": run["role"], "slot": run["slot"], "segment": run["segment"]}
            for run in runs
            if run["segment"] >= FIRST_HAND_OVER_SEGMENT
        ],
        "parked": [record["task"] for record in records if record["event"] == "task.parked"],
    }
