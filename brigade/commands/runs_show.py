from brigade.command import Argument, Command
from brigade.runs.show_run import show_run
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

ABSENT = "-"
SUMMARY_FIELDS = ("run", "procedure", "slot", "role", "project", "state", "outcome")
SUMMARY_WIDTH = max(len(field) for field in SUMMARY_FIELDS)
SEGMENT_COLUMNS = ("segment", "outcome")
RECORD_SEPARATOR = "  "


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def _render_record(record: dict) -> str:
    return RECORD_SEPARATOR.join((record["at"], str(record["segment"]), record["kind"], record["summary"]))


def _render_text(document: dict) -> str:
    summary = [
        f"{field:<{SUMMARY_WIDTH}}{RECORD_SEPARATOR}{_render_value(document['run'][field])}" for field in SUMMARY_FIELDS
    ]
    segments = render_table(
        SEGMENT_COLUMNS,
        [(str(segment["segment"]), _render_value(segment["outcome"])) for segment in document["segments"]],
    )
    lines = [*summary, "", segments]
    if document["journal"] is not None:
        lines += ["", *(_render_record(record) for record in document["journal"])]
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def runs_show(request, runtime: Runtime) -> dict:
    return show_run(runtime.paths.state_root, request.run, request.log)


COMMAND = Command(
    path=("runs", "show"),
    help="print the summary of a run and its segments, and with --log its journal",
    group_help="list the runs and show one",
    arguments=(
        Argument(("run",)),
        Argument(("--log",), {"action": "store_true", "help": "add the journal of the run, one line per record"}),
    ),
    run=runs_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
