import argparse


def read_positive_count(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"{text!r} is not a count of 1 or more")
    return int(text)
