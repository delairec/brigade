from brigade.command import Command
from brigade.runs.list_runs import list_runs
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
NO_RUNS = "no runs"
COLUMNS = ("run", "procedure", "slot", "role", "project", "state", "outcome")


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def _render_text(document: dict) -> str:
    if not document["runs"]:
        return NO_RUNS
    return render_table(
        COLUMNS, [tuple(_render_value(listed[column]) for column in COLUMNS) for listed in document["runs"]]
    )


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def runs_list(request, runtime) -> dict:
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "runs": list_runs(runtime.paths.state_root)}


COMMAND = Command(
    path=("runs", "list"),
    help="list every run with its state and outcome",
    group_help="list the runs and print their logs",
    run=runs_list,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
