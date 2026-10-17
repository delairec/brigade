from brigade.ledger.wave_started import WaveStarted

WAVE_NUMBER_MARK = "_w"


def name_next_wave(project: str, entries: tuple) -> str:
    prefix = f"{project}{WAVE_NUMBER_MARK}"
    numbers = [
        int(entry.event.wave.removeprefix(prefix))
        for entry in entries
        if isinstance(entry.event, WaveStarted) and entry.event.project == project
    ]
    return f"{prefix}{max(numbers, default=0) + 1}"
