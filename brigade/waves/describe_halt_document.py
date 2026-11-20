from datetime import datetime

from brigade.waves.describe_wave_halt import describe_wave_halt
from brigade.waves.read_wave_pause import WavePause


def describe_halt_document(wave: str, halt: dict) -> str:
    resume_at = None if halt["resume_at"] is None else datetime.fromisoformat(halt["resume_at"])
    return describe_wave_halt(wave, WavePause(reason=halt["reason"], resume_at=resume_at))
