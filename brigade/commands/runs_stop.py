from brigade.command import Argument, Command
from brigade.runs.stop_run import stop_run
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    run = document["run"]
    return f"run {run['run']} {run['state']} on {run['outcome']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def runs_stop(request, runtime: Runtime) -> dict:
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "run": stop_run(runtime.paths.state_root, request.run)}


COMMAND = Command(
    path=("runs", "stop"),
    help="stop a run: its client's group gets SIGTERM, then SIGKILL after the grace",
    group_help="list the runs and show one",
    arguments=(Argument(("run",)),),
    run=runs_stop,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
