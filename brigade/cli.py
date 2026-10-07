import argparse
import contextlib
import functools
import importlib
import json
import sys
import traceback
from importlib.resources import files
from pathlib import Path

from brigade import VERSION
from brigade.add_command_parsers import add_command_parsers
from brigade.errors import BrigadeError, CannotWrite, StandingDown, UsageError
from brigade.runtime import Invocation, Runtime, build_runtime
from brigade.system.remove_expired_trails import remove_expired_trails
from brigade.system.trail_locations import COMMANDS_DIRECTORY, TRAIL_INSTANT_FORMAT, TRAIL_SUFFIX

COMMANDS_PACKAGE = "brigade.commands"
MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"
PASSTHROUGH_SEPARATOR = "--"
USAGE_EXIT_CODE = 2
UNEXPECTED_ERROR_EXIT_CODE = 70
JSON_HELP = "print the output as a JSON document"
VERBOSE_HELP = "print every subprocess the command runs on stderr"


def _discover_commands() -> list:
    return [
        importlib.import_module(f"{COMMANDS_PACKAGE}.{name.removesuffix(MODULE_SUFFIX)}").COMMAND
        for name in sorted(entry.name for entry in files(COMMANDS_PACKAGE).iterdir())
        if name.endswith(MODULE_SUFFIX) and not name.startswith(PRIVATE_MODULE_PREFIX)
    ]


def _create_common_options():
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=JSON_HELP)
    common_options.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help=VERBOSE_HELP)
    return common_options


def _create_parser(commands):
    parser = argparse.ArgumentParser(prog="brigade")
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
    instant = runtime.now.strftime(TRAIL_INSTANT_FORMAT)
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
    document = _run_and_settle_trail(command, options)
    for diagnostic in command.describe_diagnostics(document):
        sys.stderr.write(f"brigade {_name(command)}: {diagnostic}\n")
    if command.render_passed_stderr is not None:
        sys.stdout.write(command.render_text(document))
        sys.stderr.write(command.render_passed_stderr(document))
    elif getattr(options, "json", False):
        print(json.dumps(document))
    elif getattr(options, "markdown", False):
        print(command.render_markdown(document))
    else:
        print(command.render_text(document))
    return command.decide_exit_code(document)


def _accepts(command, extras: list[str]) -> bool:
    return (
        command is not None
        and command.accept_extra_argument is not None
        and all(command.accept_extra_argument(extra) for extra in extras)
    )


def main(arguments: list[str]) -> int:
    commands = _discover_commands()
    passthroughs = [command for command in commands if command.render_passed_stderr is not None]
    parser = _create_parser([command for command in commands if command.render_passed_stderr is None])
    passthrough = _find_passthrough(arguments, passthroughs)
    separator = arguments.index(PASSTHROUGH_SEPARATOR) if passthrough is not None else len(arguments)
    options, extras = parser.parse_known_args(arguments[:separator])
    if extras and not _accepts(options.command, extras):
        parser.error(f"unrecognized arguments: {' '.join(extras)}")
    if options.command is None:
        if not options.version:
            parser.error("no option given")
        print(_describe_version(options.json))
        return 0
    command = options.command if passthrough is None else passthrough
    options.extra_arguments = extras
    options.passed_arguments = tuple(arguments[separator + 1 :])
    options.create_runtime = functools.partial(
        build_runtime, Invocation(command=_name(command), verbose=getattr(options, "verbose", False))
    )
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
