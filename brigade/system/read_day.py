import argparse
from datetime import UTC, date, datetime

DAY_FORMAT = "%Y-%m-%d"


def read_day(text: str) -> date:
    try:
        return datetime.strptime(text, DAY_FORMAT).replace(tzinfo=UTC).date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a day YYYY-MM-DD") from None
