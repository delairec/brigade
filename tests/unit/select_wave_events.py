from collections.abc import Iterable

WAVE_OUTCOMES = ("wave.pr_retargeted", "wave.merged", "wave.closed")


def select_wave_events(events: Iterable[dict]) -> list[dict]:
    return [event for event in events if event["event"] in WAVE_OUTCOMES]
