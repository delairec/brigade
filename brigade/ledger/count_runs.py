from collections.abc import Iterable
from typing import NamedTuple


class RunCount(NamedTuple):
    runs: int
    costless: int


def count_runs(segments: Iterable[dict]) -> RunCount:
    finished = list(segments)
    runs = {segment["run"] for segment in finished}
    costless = {segment["run"] for segment in finished if segment.get("cost_usd") is None}
    return RunCount(runs=len(runs), costless=len(costless))
