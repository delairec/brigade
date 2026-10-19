import argparse
import json
from dataclasses import dataclass
from typing import TextIO

from brigade.command import Command

LINE_END = "\n"


@dataclass(frozen=True)
class OutputStreams:
    stdout: TextIO
    stderr: TextIO


def _render(command: Command, document, options: argparse.Namespace) -> str:
    if getattr(options, "json", False):
        return json.dumps(document)
    if getattr(options, "markdown", False):
        return command.render_markdown(document)
    return command.render_text(document)


def write_command_output(command: Command, result, options: argparse.Namespace, streams: OutputStreams) -> int:
    for diagnostic in command.describe_diagnostics(result):
        streams.stderr.write(f"brigade {' '.join(command.path)}: {diagnostic}{LINE_END}")
    document = command.select_document(result)
    if command.render_passed_stderr is not None:
        streams.stdout.write(command.render_text(document))
        streams.stderr.write(command.render_passed_stderr(document))
    else:
        streams.stdout.write(f"{_render(command, document, options)}{LINE_END}")
    return command.decide_exit_code(document)
