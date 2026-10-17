from brigade.ledger.wave_started import WaveStarted

WAVE_NUMBER_MARK = "_w"


def name_next_wave(project: str, events: tuple) -> str:
    prefix = f"{project}{WAVE_NUMBER_MARK}"
    numbers = [
        int(event.wave.removeprefix(prefix))
        for event in events
        if isinstance(event, WaveStarted) and event.project == project
    ]
    return f"{prefix}{max(numbers, default=0) + 1}"
