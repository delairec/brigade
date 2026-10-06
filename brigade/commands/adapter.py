import json

from brigade.errors import BrigadeError
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.client_shapes import CLIENT_REQUEST_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATIONS = ("probe", "launch-argv", "parse-result", "resume-argv", "transcripts")
PROBE_REQUEST = {"schema_version": 1}


def _read_client_request(request) -> dict:
    if request.operation == "probe":
        return PROBE_REQUEST
    try:
        document = json.loads(request.stdin)
    except json.JSONDecodeError as error:
        raise BrigadeError(f"the request on stdin is not JSON: {error}") from None
    try:
        validate_document(document, CLIENT_REQUEST_SHAPES[request.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(f"the request on stdin: {problem}") from None
    return document


def run(request, runtime) -> dict:
    return ask_configured_client(runtime, request.operation, _read_client_request(request)).document
