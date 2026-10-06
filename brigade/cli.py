import argparse
import json
import sys
import traceback
from dataclasses import dataclass
from typing import Callable

from brigade import VERSION
from brigade.commands import adapter, doctor, init
from brigade.commands.render_adapter_text import render_adapter_text
from brigade.commands.render_doctor_text import render_doctor_text
from brigade.commands.render_init_text import render_init_text
from brigade.errors import BrigadeError
from brigade.runtime import build_runtime


def _create_common_options():
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="print the output as a JSON document"
    )
    return common_options


def _create_parser():
    parser = argparse.ArgumentParser(prog="brigade")
    parser.add_argument("--version", action="store_true", help="print the version of brigade")
    parser.add_argument("--json", action="store_true", help="print the output as a JSON document")
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.add_parser(
        "doctor",
        parents=[_create_common_options()],
        help="check the prerequisites and report the optional items with their fallback",
    )
    commands.add_parser(
        "init",
        parents=[_create_common_options()],
        help="create the operational corpus repository, its schema and config.toml",
    )
    adapter_parser = commands.add_parser(
        "adapter",
        parents=[_create_common_options()],
        help="answer one operation of the configured client adapter, the request read on stdin",
    )
    adapter_parser.add_argument("operation", choices=adapter.OPERATIONS)
    return parser


def _describe_version(as_json):
    if as_json:
        return json.dumps({"schema_version": 1, "version": VERSION})
    return f"brigade {VERSION}"


def _decide_doctor_exit_code(document: dict) -> int:
    if any(item["state"] == "finding" for item in document["items"]):
        return 1
    return 0


def _decide_done(document: dict) -> int:
    return 0


def _keep_options(options: argparse.Namespace) -> argparse.Namespace:
    return options


def _read_adapter_request(options: argparse.Namespace) -> argparse.Namespace:
    stdin = None if options.operation == "probe" else sys.stdin.read()
    return argparse.Namespace(**vars(options), stdin=stdin)


@dataclass(frozen=True)
class Command:
    read_request: Callable[[argparse.Namespace], object]
    run: Callable[[object, object], dict]
    render_text: Callable[[dict], str]
    decide_exit_code: Callable[[dict], int]


COMMANDS = {
    "doctor": Command(_keep_options, doctor.run, render_doctor_text, _decide_doctor_exit_code),
    "init": Command(_keep_options, init.run, render_init_text, _decide_done),
    "adapter": Command(_read_adapter_request, adapter.run, render_adapter_text, _decide_done),
}
UNEXPECTED_ERROR_EXIT_CODE = 70


def _run_command(options: argparse.Namespace) -> int:
    command = COMMANDS[options.command]
    document = command.run(command.read_request(options), build_runtime())
    if getattr(options, "json", False):
        print(json.dumps(document))
    else:
        print(command.render_text(document))
    return command.decide_exit_code(document)


def main(arguments: list[str]) -> int:
    parser = _create_parser()
    options = parser.parse_args(arguments)
    if options.command is None:
        if not options.version:
            parser.error("no option given")
        print(_describe_version(options.json))
        return 0
    try:
        return _run_command(options)
    except BrigadeError as error:
        sys.stderr.write(f"brigade {options.command}: {error}\n")
        return 1
    except Exception:
        traceback.print_exc()
        return UNEXPECTED_ERROR_EXIT_CODE
