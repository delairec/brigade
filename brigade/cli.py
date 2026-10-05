import argparse
import json
import sys

from brigade import VERSION
from brigade.commands import doctor
from brigade.commands.render_doctor_text import render_doctor_text
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
    return parser


def _describe_version(as_json):
    if as_json:
        return json.dumps({"schema_version": 1, "version": VERSION})
    return f"brigade {VERSION}"


def _decide_doctor_exit_code(document):
    if any(item["state"] == "finding" for item in document["items"]):
        return 1
    return 0


def _run_doctor(options):
    document = doctor.run(options, build_runtime())
    if getattr(options, "json", False):
        print(json.dumps(document))
    else:
        print(render_doctor_text(document))
    return _decide_doctor_exit_code(document)


def main(arguments: list[str]) -> int:
    parser = _create_parser()
    options = parser.parse_args(arguments)
    if options.command == "doctor":
        try:
            return _run_doctor(options)
        except BrigadeError as error:
            sys.stderr.write(f"brigade {options.command}: {error}\n")
            return 1
    if not options.version:
        parser.error("no option given")
    print(_describe_version(options.json))
    return 0
