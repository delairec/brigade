from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.waves.cancel_request import cancel_request

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"@REQUEST.{document['request']} {document['status']}"


def request_cancel(request, runtime: Runtime) -> dict:
    status = cancel_request(runtime, request.request)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "request": request.request, "status": status}


COMMAND = Command(
    path=("request", "cancel"),
    help="cancel a request planning or planned",
    arguments=(Argument(("request",), {"help": "the name of a REQUEST planning or planned"}),),
    run=request_cancel,
    render_text=_render_text,
)
