import argparse
import contextlib
import functools
import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import NoReturn, TextIO

from brigade import VERSION
from brigade.add_command_parsers import add_command_parsers
from brigade.errors import BrigadeError, CannotWrite, StandingDown, UsageError
from brigade.list_command_modules import COMMANDS_PACKAGE, list_command_modules
from brigade.runtime import Invocation, Runtime, build_runtime
from brigade.select_command_modules import PASSTHROUGH_SEPARATOR, select_command_modules
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT
from brigade.system.remove_expired_trails import remove_expired_trails
from brigade.system.trail_locations import COMMANDS_DIRECTORY, TRAIL_SUFFIX
from brigade.write_command_output import OutputStreams, write_command_output

USAGE_EXIT_CODE = 2
UNEXPECTED_ERROR_EXIT_CODE = 70
JSON_HELP = "print the output as a JSON document"
VERBOSE_HELP = "print every subprocess the command runs on stderr"


class _ParseDeferred(Exception):
    pass


class _DeferringArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ParseDeferred(message)

    def print_help(self, file: TextIO | None = None) -> NoReturn:
        raise _ParseDeferred


def _import_commands(module_names: list[str]) -> list:
    return [importlib.import_module(f"{COMMANDS_PACKAGE}.{name}").COMMAND for name in module_names]


def _create_common_options():
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=JSON_HELP)
    common_options.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help=VERBOSE_HELP)
    return common_options


def _create_parser(commands, parser_class):
    parser = parser_class(prog="brigade")
    parser.add_argument("--version", action="store_true", help="print the version of brigade")
    parser.add_argument("--json", action="store_true", help=JSON_HELP)
    parser.add_argument("--verbose", action="store_true", help=VERBOSE_HELP)
    add_command_parsers(parser, commands, _create_common_options())
    return parser


def _describe_version(as_json):
    if as_json:
        return json.dumps({"schema_version": 1, "version": VERSION})
    return f"brigade {VERSION}"


def _name(command) -> str:
    return " ".join(command.path)


def _find_passthrough(arguments: list[str], passthroughs: list):
    words = tuple(argument for argument in arguments if not argument.startswith("-"))
    return next(
        (
            command
            for command in passthroughs
            if words[: len(command.path)] == command.path and PASSTHROUGH_SEPARATOR in arguments
        ),
        None,
    )


def _locate_command_trail(command, runtime: Runtime) -> Path:
    instant = runtime.now.strftime(COMPACT_INSTANT_FORMAT)
    return runtime.paths.state_root / COMMANDS_DIRECTORY / f"{instant}-{'-'.join(command.path)}{TRAIL_SUFFIX}"


def _run_and_settle_trail(command, options: argparse.Namespace):
    runtime = options.create_runtime()
    trail = _locate_command_trail(command, runtime)
    try:
        remove_expired_trails(runtime.paths, runtime.now)
        document = command.run(command.read_request(options), runtime)
    except BaseException:
        with contextlib.suppress(CannotWrite):
            runtime.trail.settle(trail)
        raise
    runtime.trail.settle(trail)
    return document


def _run_command(command, options: argparse.Namespace) -> int:
    result = _run_and_settle_trail(command, options)
    return write_command_output(command, result, options, OutputStreams(stdout=sys.stdout, stderr=sys.stderr))


def _accepts(command, extras: list[str]) -> bool:
    return (
        command is not None
        and command.accept_extra_argument is not None
        and all(command.accept_extra_argument(extra) for extra in extras)
    )


def _locate_separator(arguments: list[str], passthrough) -> int:
    return arguments.index(PASSTHROUGH_SEPARATOR) if passthrough is not None else len(arguments)


def _parse(arguments: list[str], module_names: list[str], parser_class):
    commands = _import_commands(module_names)
    passthroughs = [command for command in commands if command.render_passed_stderr is not None]
    parser = _create_parser(commands, parser_class)
    passthrough = _find_passthrough(arguments, passthroughs)
    options, extras = parser.parse_known_args(arguments[: _locate_separator(arguments, passthrough)])
    if extras and not _accepts(options.command, extras):
        parser.error(f"unrecognized arguments: {' '.join(extras)}")
    if options.command is None and not options.version:
        parser.error("no option given")
    return options, extras, passthrough


def main(arguments: list[str]) -> int:
    module_names = list_command_modules()
    try:
        options, extras, passthrough = _parse(
            arguments, select_command_modules(arguments, module_names), _DeferringArgumentParser
        )
    except _ParseDeferred:
        options, extras, passthrough = _parse(arguments, module_names, argparse.ArgumentParser)
    separator = _locate_separator(arguments, passthrough)
    if options.command is None:
        print(_describe_version(options.json))  # noqa: T201 - the module that prints the result of every command
        return 0
    command = options.command if passthrough is None else passthrough
    options.extra_arguments = extras
    options.passed_arguments = tuple(arguments[separator + 1 :])
    options.standard_input = sys.stdin
    options.create_runtime = functools.partial(
        build_runtime, Invocation(command=_name(command), verbose=getattr(options, "verbose", False))
    )
    return _run_reporting_errors(command, options)


def _run_reporting_errors(command: object, options: argparse.Namespace) -> int:
    try:
        return _run_command(command, options)
    except StandingDown as reason:
        sys.stderr.write(f"brigade {_name(command)}: {reason}\n")
        return 0
    except UsageError as error:
        sys.stderr.write(f"brigade {_name(command)}: {error}\n")
        return USAGE_EXIT_CODE
    except BrigadeError as error:
        sys.stderr.write(f"brigade {_name(command)}: {error}\n")
        return 1
    except Exception:  # noqa: BLE001 - the last resort of main: the traceback is printed, the exit code is 70
        traceback.print_exc()
        return UNEXPECTED_ERROR_EXIT_CODE
