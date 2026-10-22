from brigade.ledger.wave_pr_opened import WavePrOpened


def find_integration_pull_request(events: tuple, wave: str) -> int | None:
    opened = [event.pr for event in events if isinstance(event, WavePrOpened) and event.wave == wave]
    return opened[-1] if opened else None
