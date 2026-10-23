import argparse


def read_standard_input(options: argparse.Namespace) -> str:
    return options.standard_input.read()
