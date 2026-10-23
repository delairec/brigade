import argparse

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.studies.change_study_status import change_study_status

STATUS = "paused"


def _render_text(document: dict) -> str:
    target = f"@STUDY.{document['study']}"
    if document["changed"]:
        return f"paused {target}"
    return f"{target} is already {document['status']}"


def study_pause(request: argparse.Namespace, runtime: Runtime) -> dict:
    return change_study_status(runtime, request.name, STATUS)


COMMAND = Command(
    path=("study", "pause"),
    help="pause a study, which the tick no longer runs",
    arguments=(Argument(("name",)),),
    run=study_pause,
    render_text=_render_text,
)
