from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.merged_wave import MergedWave


def list_merged_waves(events: tuple, project: str, of_milestone: set[str]) -> tuple[MergedWave, ...]:
    closed = {event.wave: event.pr for event in events if isinstance(event, WaveClosed)}
    return tuple(
        MergedWave(wave=event.wave, pr=closed[event.wave])
        for event in events
        if isinstance(event, WaveStarted)
        and event.project == project
        and event.wave in closed
        and of_milestone.intersection(event.tasks)
    )
