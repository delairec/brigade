import argparse
import json
import sys
import traceback
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from brigade import VERSION
from brigade.commands import adapter, doctor, init, project_add, project_list, project_show, project_status
from brigade.commands import corpus, corpus_awawa
from brigade.commands import ledger, ledger_budgets, ledger_compare
from brigade.commands.describe_skipped_lines import describe_skipped_lines
from brigade.commands import roles_lint, roles_list, roles_show
from brigade.commands import scheduler_install, scheduler_status, tick
from brigade.commands import run, runs_list, runs_logs
from brigade.commands.render_adapter_text import render_adapter_text
from brigade.commands.render_corpus_text import render_corpus_text
from brigade.commands.render_doctor_text import render_doctor_text
from brigade.commands.render_init_text import render_init_text
from brigade.commands.render_ledger_budgets_text import render_ledger_budgets_text
from brigade.commands.render_ledger_compare_text import render_ledger_compare_text
from brigade.commands.render_ledger_text import render_ledger_text
from brigade.commands.render_project_add_text import render_project_add_text
from brigade.commands.render_project_list_text import render_project_list_text
from brigade.commands.render_project_show_text import render_project_show_text
from brigade.commands.render_project_status_text import render_project_status_text
from brigade.commands.render_roles_lint_text import render_roles_lint_text
from brigade.commands.render_roles_list_text import render_roles_list_text
from brigade.commands.render_roles_show_text import render_roles_show_text
from brigade.commands.render_scheduler_install_text import render_scheduler_install_text
from brigade.commands.render_scheduler_status_text import render_scheduler_status_text
from brigade.commands.render_tick_text import render_tick_text
from brigade.commands.render_run_text import render_run_text
from brigade.commands.render_runs_list_text import render_runs_list_text
from brigade.commands.render_runs_logs_text import render_runs_logs_text
from brigade.errors import BrigadeError, StandingDown, UsageError
from brigade.runtime import build_runtime
from brigade.system.read_configuration import SLOTS


DAY_FORMAT = "%Y-%m-%d"
DAYS_SUFFIX = "d"
LAST_RUNS_BY_DEFAULT = 20
ACTION_DESTINATIONS = ("project_action", "ledger_report", "roles_action", "scheduler_action", "runs_action")
CORPUS_COMMAND = "corpus"
PASSTHROUGH_SEPARATOR = "--"
RUN_ARGUMENT_SEPARATOR = "="


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


def _add_roles_parser(commands) -> None:
    roles_parser = commands.add_parser("roles", help="list, show and lint the roles each slot resolves to")
    actions = roles_parser.add_subparsers(dest="roles_action", metavar="action", required=True)
    actions.add_parser("list", parents=[_create_common_options()], help="list the role, the source and the model of each slot")
    show_parser = actions.add_parser("show", parents=[_create_common_options()], help="print the role file a slot resolves to")
    show_parser.add_argument("slot", choices=SLOTS)
    actions.add_parser("lint", parents=[_create_common_options()], help="check the built-in and the machine role files")


def _add_tick_parser(commands) -> None:
    tick_parser = commands.add_parser(
        "tick", parents=[_create_common_options()], help="plan and apply what the facts call for, once or in a loop"
    )
    modes = tick_parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--once", dest="mode", action="store_const", const="once", help="run one tick")
    modes.add_argument(
        "--dry-run", dest="mode", action="store_const", const="dry-run", help="print the snapshot and the plan"
    )
    modes.add_argument(
        "--loop", dest="mode", action="store_const", const="loop", help="run a tick every five minutes until a signal"
    )


def _add_scheduler_parser(commands) -> None:
    scheduler_parser = commands.add_parser("scheduler", help="install what fires the tick, and report it")
    actions = scheduler_parser.add_subparsers(dest="scheduler_action", metavar="action", required=True)
    actions.add_parser(
        "install", parents=[_create_common_options()], help="install the scheduler config.toml names, or the default"
    )
    actions.add_parser("status", parents=[_create_common_options()], help="report the scheduler installed")
def _add_run_parser(commands) -> None:
    run_parser = commands.add_parser(
        "run", parents=[_create_common_options()], help="run a procedure as a slot through the client adapter"
    )
    run_parser.add_argument("procedure", help="a procedure name, or the path of its Markdown file")
    run_parser.add_argument("--slot", required=True, choices=SLOTS, help="the slot the run takes its role from")
    run_parser.add_argument("--project", help="the registered project the run belongs to")
    run_parser.add_argument("--cwd", help="the directory the client runs in; the project's path, else the current one")
    run_parser.add_argument("--brief", help="a file whose text the run receives as its brief")
    run_parser.add_argument("--detach", action="store_true", help="run in the background and print the run id")
    run_parser.add_argument("--run-id", help=argparse.SUPPRESS)
    run_parser.add_argument("arguments", nargs="*", metavar="key=value", help="an argument of the procedure")


def _add_runs_parser(commands) -> None:
    runs_parser = commands.add_parser("runs", help="list the runs and print their logs")
    actions = runs_parser.add_subparsers(dest="runs_action", metavar="action", required=True)
    actions.add_parser("list", parents=[_create_common_options()], help="list every run with its state and outcome")
    logs_parser = actions.add_parser("logs", parents=[_create_common_options()], help="print the log of a run")
    logs_parser.add_argument("run")
    logs_parser.add_argument("--tail", type=_read_positive_count, help="the last N lines only")


def _add_corpus_parser(commands) -> None:
    corpus_parser = commands.add_parser(
        "corpus",
        parents=[_create_common_options()],
        help="read a registered project's tree at a branch, a SHA or a worktree; -- <awawa args> runs awawa there",
    )
    corpus_parser.add_argument("project")
    trees = corpus_parser.add_mutually_exclusive_group(required=True)
    trees.add_argument(
        "--ref", help="a branch or a SHA, extracted to the cache; worktree:<branch> reads the worktree of that branch"
    )
    trees.add_argument("--worktree", type=Path, help="the path of a worktree of the project, read in place")


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
    _add_roles_parser(commands)
    _add_tick_parser(commands)
    _add_scheduler_parser(commands)
    _add_corpus_parser(commands)
    _add_run_parser(commands)
    _add_runs_parser(commands)
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


def _decide_roles_lint_exit_code(document: dict) -> int:
    if document["findings"]:
        return 1
    return 0


def _decide_run_exit_code(document: dict) -> int:
    if document.get("outcome", "done") != "done":
        return 1
    return 0


def _describe_run_warnings(document: dict) -> list[str]:
    return document.get("warnings", [])


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
    "doctor": Command(_keep_options, doctor.doctor, render_doctor_text, _decide_doctor_exit_code),
    "init": Command(_keep_options, init.init, render_init_text, _decide_done),
    "adapter": Command(_read_adapter_request, adapter.adapter, render_adapter_text, _decide_done),
    "project add": Command(_keep_options, project_add.project_add, render_project_add_text, _decide_done),
    "project list": Command(_keep_options, project_list.project_list, render_project_list_text, _decide_done),
    "project show": Command(_keep_options, project_show.project_show, render_project_show_text, _decide_done),
    "project pause": Command(_ask_paused, project_status.project_status, render_project_status_text, _decide_done),
    "project resume": Command(_ask_active, project_status.project_status, render_project_status_text, _decide_done),
    "ledger": Command(_read_ledger_request, ledger.ledger, render_ledger_text, _decide_done, describe_skipped_lines),
    "ledger budgets": Command(
        _keep_options, ledger_budgets.ledger_budgets, render_ledger_budgets_text, _decide_done, describe_skipped_lines
    ),
    "ledger compare": Command(
        _keep_options, ledger_compare.ledger_compare, render_ledger_compare_text, _decide_done, describe_skipped_lines
    ),
    "roles list": Command(_keep_options, roles_list.roles_list, render_roles_list_text, _decide_done),
    "roles show": Command(_keep_options, roles_show.roles_show, render_roles_show_text, _decide_done),
    "roles lint": Command(_keep_options, roles_lint.roles_lint, render_roles_lint_text, _decide_roles_lint_exit_code),
    "tick": Command(_keep_options, tick.tick, render_tick_text, _decide_done),
    "scheduler install": Command(_keep_options, scheduler_install.scheduler_install, render_scheduler_install_text, _decide_done),
    "scheduler status": Command(_keep_options, scheduler_status.scheduler_status, render_scheduler_status_text, _decide_done),
    "corpus": Command(_keep_options, corpus.corpus, render_corpus_text, _decide_done),
    "run": Command(_keep_options, run.run, render_run_text, _decide_run_exit_code, _describe_run_warnings),
    "runs list": Command(_keep_options, runs_list.runs_list, render_runs_list_text, _decide_done),
    "runs logs": Command(_keep_options, runs_logs.runs_logs, render_runs_logs_text, _decide_done),
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


def _split_awawa_arguments(arguments: list[str]):
    command = next((argument for argument in arguments if not argument.startswith("-")), None)
    if command != CORPUS_COMMAND or PASSTHROUGH_SEPARATOR not in arguments:
        return arguments, None
    separator = arguments.index(PASSTHROUGH_SEPARATOR)
    return arguments[:separator], tuple(arguments[separator + 1 :])


def _pass_awawa_through(options: argparse.Namespace, awawa_arguments: tuple[str, ...]) -> int:
    request = argparse.Namespace(**vars(options), awawa_arguments=awawa_arguments)
    passage = corpus_awawa.corpus_awawa(request, build_runtime())
    sys.stderr.write(f"brigade {CORPUS_COMMAND}: @PROJECT.{passage.project} at {passage.sha}\n")
    sys.stdout.write(passage.record.stdout)
    sys.stderr.write(passage.record.stderr)
    return passage.record.exit_code


def _is_option(extra: str) -> bool:
    return extra.startswith("-") or RUN_ARGUMENT_SEPARATOR not in extra


def main(arguments: list[str]) -> int:
    parser = _create_parser()
    own_arguments, awawa_arguments = _split_awawa_arguments(arguments)
    options, extras = parser.parse_known_args(own_arguments)
    if extras and (options.command != "run" or any(_is_option(extra) for extra in extras)):
        parser.error(f"unrecognized arguments: {' '.join(extras)}")
    if options.command == "run":
        options.arguments = [*options.arguments, *extras]
    if options.command is None:
        if not options.version:
            parser.error("no option given")
        print(_describe_version(options.json))
        return 0
    try:
        if awawa_arguments is not None:
            return _pass_awawa_through(options, awawa_arguments)
        return _run_command(options)
    except StandingDown as reason:
        sys.stderr.write(f"brigade {_name_command(options)}: {reason}\n")
        return 0
    except UsageError as error:
        sys.stderr.write(f"brigade {_name_command(options)}: {error}\n")
        return USAGE_EXIT_CODE
    except BrigadeError as error:
        sys.stderr.write(f"brigade {_name_command(options)}: {error}\n")
        return 1
    except Exception:
        traceback.print_exc()
        return UNEXPECTED_ERROR_EXIT_CODE
