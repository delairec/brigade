from typing import Iterable, Optional

PERCENTILES = {"p50": 50, "p90": 90}


def _take_nearest_rank(measured: list[int], percentile: int) -> Optional[int]:
    if not measured:
        return None
    rank = -(-percentile * len(measured) // 100)
    return measured[rank - 1]


def summarize_steps(steps: Iterable[Optional[int]]) -> dict:
    all_steps = list(steps)
    measured = sorted(step for step in all_steps if step is not None)
    return {
        "measured": len(measured),
        "unmeasured": len(all_steps) - len(measured),
        **{name: _take_nearest_rank(measured, percentile) for name, percentile in PERCENTILES.items()},
    }
