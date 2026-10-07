import argparse
from datetime import timedelta

from brigade.system.read_day import read_day

DAYS_SUFFIX = "d"


def read_since(text: str):
    count = text.removesuffix(DAYS_SUFFIX)
    if text.endswith(DAYS_SUFFIX) and count.isdigit():
        return timedelta(days=int(count))
    try:
        return read_day(text)
    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(f"{text!r} is neither <n>d nor a day YYYY-MM-DD") from None
