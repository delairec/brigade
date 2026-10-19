import argparse
from dataclasses import dataclass
from typing import TextIO

from brigade.command import Command


@dataclass(frozen=True)
class OutputStreams:
    stdout: TextIO
    stderr: TextIO


def write_command_output(command: Command, result, options: argparse.Namespace, streams: OutputStreams) -> int:
    raise NotImplementedError
