import argparse
import json
import sys
import traceback
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable

from brigade import VERSION
from brigade.commands import adapter, doctor, init, project_add, project_list, project_show, project_status
from brigade.commands import ledger, ledger_budgets, ledger_compare
from brigade.commands.describe_skipped_lines import describe_skipped_lines
from brigade.commands.render_adapter_text import render_adapter_text
from brigade.commands.render_doctor_text import render_doctor_text
from brigade.commands.render_init_text import render_init_text
from brigade.commands.render_ledger_budgets_text import render_ledger_budgets_text
from brigade.commands.render_ledger_compare_text import render_ledger_compare_text
from brigade.commands.render_ledger_text import render_ledger_text
from brigade.commands.render_project_add_text import render_project_add_text
from brigade.commands.render_project_list_text import render_project_list_text
from brigade.commands.render_project_show_text import render_project_show_text
from brigade.commands.render_project_status_text import render_project_status_text
from brigade.errors import BrigadeError, UsageError
from brigade.runtime import build_runtime


DAY_FORMAT = "%Y-%m-%d"
DAYS_SUFFIX = "d"
LAST_RUNS_BY_DEFAULT = 20
ACTION_DESTINATIONS = ("project_action", "ledger_report")


def _create_common_options():
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="print the output as a JSON document"
    )
    return common_options


def _add_project_parser(commands) -> None:
    project_parser = commands.add_parser("project", help="register the projects brigade works on, list and show them")
    actions = project_parser.add_subparsers(dest="project_action", metavar="action", required=True)
    add_parser = actions.add_parser(
        "add", parents=[_create_common_options()], help="register a git repository in the operational corpus"
    )
    add_parser.add_argument("path")
    add_parser.add_argument("--name", help="the name of the PROJECT entity; the basename of the path by default")
    add_parser.add_argument("--acceptance", action="append", default=[], help="a light command run by task check")
    add_parser.add_argument("--heavy", action="append", default=[], help="a suite left to continuous integration")
    add_parser.add_argument("--setup", action="append", default=[], help="a per-worktree command")
    add_parser.add_argument("--force", action="store_true", help="replace the project already registered")
    actions.add_parser("list", parents=[_create_common_options()], help="list every registered project")
    for action, help_text in (
        ("show", "print the fields of a project"),
        ("pause", "pause a project"),
        ("resume", "resume a paused project"),
    ):
        action_parser = actions.add_parser(action, parents=[_create_common_options()], help=help_text)
        action_parser.add_argument("name")


def _read_positive_count(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"{text!r} is not a count of 1 or more")
    return int(text)


def _read_day(text: str) -> date:
    try:
        return datetime.strptime(text, DAY_FORMAT).date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a day YYYY-MM-DD") from None


def _read_since(text: str):
    count = text.removesuffix(DAYS_SUFFIX)
    if text.endswith(DAYS_SUFFIX) and count.isdigit():
        return timedelta(days=int(count))
    try:
        return _read_day(text)
    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(f"{text!r} is neither <n>d nor a day YYYY-MM-DD") from None


def _add_ledger_parser(commands) -> None:
    ledger_parser = commands.add_parser(
        "ledger", parents=[_create_common_options()], help="read the event journal: an overview, a wave or a project"
    )
    views = ledger_parser.add_mutually_exclusive_group()
    views.add_argument("--wave", help="the tasks, steps, pauses, hand-overs and parked tasks of a wave")
    views.add_argument("--project", help="the waves, orders, pull requests, signals, patterns and constraints of a project")
    ledger_parser.add_argument("--since", type=_read_since, help="with --project, <n>d or a day YYYY-MM-DD in UTC")
    reports = ledger_parser.add_subparsers(dest="ledger_report", metavar="report")
    budgets_parser = reports.add_parser(
        "budgets", parents=[_create_common_options()], help="p50 and p90 steps per procedure over its last runs"
    )
    budgets_parser.add_argument(
        "--last", type=_read_positive_count, default=LAST_RUNS_BY_DEFAULT, help="the runs of each procedure, 20 by default"
    )
    compare_parser = reports.add_parser(
        "compare", parents=[_create_common_options()], help="the runs before a day against the runs from that day on"
    )
    compare_parser.add_argument("--before", type=_read_day, required=True, help="a day YYYY-MM-DD in UTC")


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
    _add_project_parser(commands)
    _add_ledger_parser(commands)
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


def _ask_paused(options: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(**vars(options), status="paused")


def _ask_active(options: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(**vars(options), status="active")


def _read_ledger_request(options: argparse.Namespace) -> argparse.Namespace:
    if options.since is not None and options.project is None:
        raise UsageError("--since needs --project")
    return options


def _read_adapter_request(options: argparse.Namespace) -> argparse.Namespace:
    stdin = None if options.operation == "probe" else sys.stdin.read()
    return argparse.Namespace(**vars(options), stdin=stdin)


def _describe_no_diagnostics(document: dict) -> list[str]:
    return []


@dataclass(frozen=True)
class Command:
    read_request: Callable[[argparse.Namespace], object]
    run: Callable[[object, object], dict]
    render_text: Callable[[dict], str]
    decide_exit_code: Callable[[dict], int]
    describe_diagnostics: Callable[[dict], list[str]] = _describe_no_diagnostics


COMMANDS = {
    "doctor": Command(_keep_options, doctor.run, render_doctor_text, _decide_doctor_exit_code),
    "init": Command(_keep_options, init.run, render_init_text, _decide_done),
    "adapter": Command(_read_adapter_request, adapter.run, render_adapter_text, _decide_done),
    "project add": Command(_keep_options, project_add.run, render_project_add_text, _decide_done),
    "project list": Command(_keep_options, project_list.run, render_project_list_text, _decide_done),
    "project show": Command(_keep_options, project_show.run, render_project_show_text, _decide_done),
    "project pause": Command(_ask_paused, project_status.run, render_project_status_text, _decide_done),
    "project resume": Command(_ask_active, project_status.run, render_project_status_text, _decide_done),
    "ledger": Command(_read_ledger_request, ledger.run, render_ledger_text, _decide_done, describe_skipped_lines),
    "ledger budgets": Command(
        _keep_options, ledger_budgets.run, render_ledger_budgets_text, _decide_done, describe_skipped_lines
    ),
    "ledger compare": Command(
        _keep_options, ledger_compare.run, render_ledger_compare_text, _decide_done, describe_skipped_lines
    ),
}
USAGE_EXIT_CODE = 2
UNEXPECTED_ERROR_EXIT_CODE = 70


def _name_command(options: argparse.Namespace) -> str:
    actions = [getattr(options, name) for name in ACTION_DESTINATIONS if getattr(options, name, None) is not None]
    return " ".join([options.command, *actions])


def _run_command(options: argparse.Namespace) -> int:
    name = _name_command(options)
    command = COMMANDS[name]
    document = command.run(command.read_request(options), build_runtime())
    for diagnostic in command.describe_diagnostics(document):
        sys.stderr.write(f"brigade {name}: {diagnostic}\n")
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
    except UsageError as error:
        sys.stderr.write(f"brigade {_name_command(options)}: {error}\n")
        return USAGE_EXIT_CODE
    except BrigadeError as error:
        sys.stderr.write(f"brigade {_name_command(options)}: {error}\n")
        return 1
    except Exception:
        traceback.print_exc()
        return UNEXPECTED_ERROR_EXIT_CODE
