from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.waves.start_wave import start_wave

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return (
        f"@REQUEST.{document['request']} {document['status']},"
        f" wave @MILESTONE.{document['milestone']} of @PROJECT.{document['project']}"
    )


def _decide_exit_code(document: dict) -> int:
    return 0


def wave_start(request, runtime: Runtime) -> dict:
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **start_wave(runtime, request.request)}


COMMAND = Command(
    path=("wave", "start"),
    help="start the wave of a planned request",
    arguments=(Argument(("request",), {"help": "the name of a planned REQUEST"}),),
    run=wave_start,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
