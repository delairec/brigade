from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.read_task_states import read_task_states

MERGED_STATE = "merged"


def describe_last_closed_wave(entries: tuple[LedgerEntry, ...]) -> dict | None:
    started = {entry.event.wave: entry.event for entry in entries if isinstance(entry.event, WaveStarted)}
    closed = [entry for entry in entries if isinstance(entry.event, WaveClosed) and entry.event.wave in started]
    if not closed:
        return None
    last = closed[-1]
    wave = started[last.event.wave]
    states = read_task_states(entries, wave.wave)
    return {
        "wave": wave.wave,
        "project": wave.project,
        "closed_at": format_instant(last.instant),
        "tasks": len(wave.tasks),
        "merged": sum(states.get(task) == MERGED_STATE for task in wave.tasks),
    }
