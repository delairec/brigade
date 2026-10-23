from brigade.command import Argument, Command
from brigade.runs.stop_run import SYSTEM_PROCESS_SIGNALLER, stop_run
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    run = document["run"]
    return f"run {run['run']} {run['state']} on {run['outcome']}"


def runs_stop(request, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": stop_run(runtime.paths.state_root, request.run, SYSTEM_PROCESS_SIGNALLER),
    }


COMMAND = Command(
    path=("runs", "stop"),
    help="stop a run: its client's group gets SIGTERM, then SIGKILL after the grace",
    group_help="list the runs, show one, stop one and prune them",
    arguments=(Argument(("run",)),),
    run=runs_stop,
    render_text=_render_text,
)
