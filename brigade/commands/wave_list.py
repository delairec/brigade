from brigade.command import Argument, Command
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.summarize_waves import WaveSummary, summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("wave", "project", "branch", "last event", "tasks")
COLUMNS = ("wave", "project", "branch", "last_event", "tasks")


def _render_text(document: dict) -> str:
    return render_table(HEADER, [tuple(str(row[column]) for column in COLUMNS) for row in document["waves"]])


def _is_ended(summary: WaveSummary) -> bool:
    return not summary.is_open


def wave_list(request, runtime: Runtime) -> dict:
    summaries = sorted(summarize_waves(read_ledger(runtime.paths.state_root).entries), key=_is_ended)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "waves": [
            {
                "wave": summary.started.wave,
                "project": summary.started.project,
                "branch": summary.started.branch,
                "last_event": summary.last_event,
                "tasks": len(summary.started.tasks),
            }
            for summary in summaries
            if request.project in (None, summary.started.project)
        ],
    }


COMMAND = Command(
    path=("wave", "list"),
    help="print one row per wave of the ledger, the open waves first",
    arguments=(Argument(("--project",), {"help": "only the waves of this registered project"}),),
    run=wave_list,
    render_text=_render_text,
)
