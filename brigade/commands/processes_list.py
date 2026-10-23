from brigade.command import Command
from brigade.processes.list_invocations import list_invocations
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
COLUMNS = ("kind", "id", "instant", "processes", "failed")


def _render_text(document: dict) -> str:
    return render_table(
        COLUMNS, [tuple(str(invocation[column]) for column in COLUMNS) for invocation in document["invocations"]]
    )


def processes_list(request, runtime: Runtime) -> dict:
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "invocations": list_invocations(runtime.paths.state_root)}


COMMAND = Command(
    path=("processes", "list"),
    help="list every run, tick and command that left processes, newest first, with its count of failed ones",
    group_help="list the subprocesses brigade started and show those of one run, tick or command",
    run=processes_list,
    render_text=_render_text,
)
