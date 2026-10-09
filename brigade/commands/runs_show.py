import sys
from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import UsageError
from brigade.runs.describe_run import describe_run
from brigade.runs.run_follower import RunFollower
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runs.show_run import show_run
from brigade.runtime import Runtime
from brigade.system.poll_until_signalled import poll_until_signalled
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
SUMMARY_FIELDS = ("run", "procedure", "slot", "role", "project", "state", "outcome")
SUMMARY_WIDTH = max(len(field) for field in SUMMARY_FIELDS)
ENDING_FIELDS = ("state", "outcome")
SEGMENT_COLUMNS = ("segment", "outcome")
RECORD_SEPARATOR = "  "
LINE_END = "\n"
RUNNING = "running"
NO_JOURNAL_YET = ()


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def _render_field(run: dict, field: str) -> str:
    return f"{field:<{SUMMARY_WIDTH}}{RECORD_SEPARATOR}{_render_value(run[field])}"


def _render_record(record: dict) -> str:
    return RECORD_SEPARATOR.join((record["at"], str(record["segment"]), record["kind"], record["summary"]))


def _render_text(document: dict) -> str:
    if "interrupted" in document:
        return "\n".join(["", *(_render_field(document["run"], field) for field in ENDING_FIELDS)])
    summary = [_render_field(document["run"], field) for field in SUMMARY_FIELDS]
    segments = render_table(
        SEGMENT_COLUMNS,
        [(str(segment["segment"]), _render_value(segment["outcome"])) for segment in document["segments"]],
    )
    lines = [*summary, "", segments]
    if document["journal"] is not None:
        lines += ["", *(_render_record(record) for record in document["journal"])]
    return "\n".join(lines)


def _read_request(options):
    if options.follow and getattr(options, "json", False):
        raise UsageError("--follow and --json exclude each other")
    return options


def _decide_exit_code(document: dict) -> int:
    if "interrupted" not in document or document["interrupted"] or document["run"]["outcome"] == "done":
        return 0
    return 1


def _print(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


class _FollowPrinter:
    def __init__(self, state_root: Path, run_id: str):
        self.state_root = state_root
        self.run_id = run_id
        self.follower = RunFollower(state_root / RUNS_DIRECTORY / run_id, describe_run)
        self.opened = False

    def poll(self) -> bool:
        if not self.opened:
            opening = show_run(self.state_root, self.run_id, with_journal=False)
            _print(_render_text({**opening, "journal": NO_JOURNAL_YET}) + LINE_END)
            self.opened = True
        _print("".join(_render_record(record) + LINE_END for record in self.follower.read_records()))
        return self.follower.run["state"] != RUNNING


def _follow_run(run_id: str, runtime: Runtime) -> dict:
    printer = _FollowPrinter(runtime.paths.state_root, run_id)
    interval_s = read_optional_configuration(runtime.paths.configuration_file).journal_poll_s
    interrupted = poll_until_signalled(printer.poll, interval_s)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "run": printer.follower.run, "interrupted": interrupted}


def runs_show(request, runtime: Runtime) -> dict:
    if request.follow:
        return _follow_run(request.run, runtime)
    return show_run(runtime.paths.state_root, request.run, request.log)


COMMAND = Command(
    path=("runs", "show"),
    help="print the summary of a run and its segments, and with --log its journal",
    group_help="list the runs and show one",
    arguments=(
        Argument(("run",)),
        Argument(("--log",), {"action": "store_true", "help": "add the journal of the run, one line per record"}),
        Argument(
            ("--follow",), {"action": "store_true", "help": "print the journal as it is written, until the run ends"}
        ),
    ),
    run=runs_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
