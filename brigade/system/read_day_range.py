import argparse
from dataclasses import dataclass
from datetime import date

from brigade.system.read_day import read_day

RANGE_SEPARATOR = ".."


@dataclass(frozen=True)
class DayRange:
    start: date
    end: date


def read_day_range(text: str) -> DayRange:
    start, _, end = text.partition(RANGE_SEPARATOR)
    try:
        return DayRange(start=read_day(start), end=read_day(end))
    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a range START..END of days YYYY-MM-DD") from None
