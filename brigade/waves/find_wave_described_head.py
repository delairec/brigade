from brigade.ledger.wave_pr_described import WavePrDescribed


def find_wave_described_head(events: tuple, wave: str, pr: int) -> str | None:
    heads = [
        event.head for event in events if isinstance(event, WavePrDescribed) and event.wave == wave and event.pr == pr
    ]
    return heads[-1] if heads else None
