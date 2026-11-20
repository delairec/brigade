from datetime import datetime

from brigade.tick.actions import PauseWave
from brigade.tick.build_snapshot import Snapshot
from brigade.waves.read_wave_pause import WavePause


def _read_halt(pause: PauseWave) -> WavePause:
    return WavePause(
        reason=pause.reason, resume_at=None if pause.resume_at is None else datetime.fromisoformat(pause.resume_at)
    )


def read_planned_halts(snapshot: Snapshot, actions: tuple) -> dict[str, WavePause]:
    held = {wave.wave: wave.pause for wave in snapshot.waves if wave.pause is not None}
    planned = {action.wave: _read_halt(action) for action in actions if isinstance(action, PauseWave)}
    return planned | held
