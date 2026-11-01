from collections.abc import Iterable


def sum_reported(values: Iterable[float | None]) -> float | None:
    reported = [value for value in values if value is not None]
    if not reported:
        return None
    return sum(reported)
