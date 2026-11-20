from brigade.ledger.format_instant import format_instant
from brigade.waves.read_wave_pause import WavePause


def describe_wave_halt(wave: str, halt: WavePause) -> str:
    if halt.resume_at is None:
        return f"wave {wave} parked: {halt.reason}; it waits for brigade wave resume {wave}"
    return f"wave {wave} blocked until {format_instant(halt.resume_at)}: {halt.reason}"
