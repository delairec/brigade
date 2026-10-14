import shlex

from brigade.command import Argument, Command
from brigade.processes.show_invocation import show_invocation
from brigade.runtime import Runtime

ABSENT = "-"
RECORD_SEPARATOR = "  "


def _render_measure(record: dict) -> str:
    if record["exit"] is not None:
        return str(record["exit"])
    if record["duration_ms"] is not None:
        return f"{record['duration_ms']} ms"
    return ABSENT


def _render_record(record: dict) -> str:
    return RECORD_SEPARATOR.join((record["outcome"], _render_measure(record), shlex.join(record["argv"])))


def _render_text(document: dict) -> str:
    return "\n".join(_render_record(record) for record in document["processes"])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def processes_show(request, runtime: Runtime) -> dict:
    return show_invocation(runtime.paths.state_root, request.id, failed_only=request.failed)


COMMAND = Command(
    path=("processes", "show"),
    help="print the subprocesses a run, a tick or a command started, one line per process",
    group_help="list the subprocesses brigade started and show those of one run, tick or command",
    arguments=(
        Argument(("id",), {"help": "a run id, or the id brigade processes list prints for a tick or a command"}),
        Argument(("--failed",), {"action": "store_true", "help": "keep the processes not exited with code 0"}),
    ),
    run=processes_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
