from collections import Counter
from collections.abc import Iterable


def count_by_name(names: Iterable) -> dict:
    return dict(sorted(Counter(names).items(), key=lambda item: str(item[0])))
