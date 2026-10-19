from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.waves.start_wave import start_wave

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return (
        f"@REQUEST.{document['request']} {document['status']}, wave {document['wave']},"
        f" @MILESTONE.{document['milestone']} of @PROJECT.{document['project']}"
    )


def _decide_exit_code(document: dict) -> int:
    return 0


def wave_start(request, runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **start_wave(runtime, configuration, request.request)}


COMMAND = Command(
    path=("wave", "start"),
    help="start the wave of a planned request",
    group_help="start the waves of the planned requests, list and show them",
    arguments=(Argument(("request",), {"help": "the name of a planned REQUEST"}),),
    run=wave_start,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
