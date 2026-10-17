from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.studies.change_study_status import change_study_status

STATUS = "active"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    target = f"@STUDY.{document['study']}"
    if document["changed"]:
        return f"resumed {target}"
    return f"{target} is already {document['status']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def study_resume(request, runtime: Runtime) -> dict:
    return change_study_status(runtime, request.name, STATUS)


COMMAND = Command(
    path=("study", "resume"),
    help="resume a paused study",
    arguments=(Argument(("name",)),),
    run=study_resume,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
