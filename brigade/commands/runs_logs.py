from brigade.command import Argument, Command
from brigade.runs.read_run_logs import read_run_logs
from brigade.system.read_positive_count import read_positive_count

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return "\n".join(document["lines"])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def runs_logs(request, runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": request.run,
        "lines": read_run_logs(runtime.paths.state_root, request.run, request.tail),
    }


COMMAND = Command(
    path=("runs", "logs"),
    help="print the log of a run",
    group_help="list the runs and print their logs",
    arguments=(
        Argument(("run",)),
        Argument(("--tail",), {"type": read_positive_count, "help": "the last N lines only"}),
    ),
    run=runs_logs,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
