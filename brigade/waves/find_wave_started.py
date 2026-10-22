from brigade.ledger.wave_started import WaveStarted


def find_wave_started(events: tuple, wave: str) -> WaveStarted:
    return next(event for event in events if isinstance(event, WaveStarted) and event.wave == wave)
