from brigade.ledger.wave_started import WaveStarted


def find_wave_name(events: tuple, project: str, branch: str) -> str | None:
    return next(
        (
            event.wave
            for event in reversed(events)
            if isinstance(event, WaveStarted) and event.project == project and event.branch == branch
        ),
        None,
    )
