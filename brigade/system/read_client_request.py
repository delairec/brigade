import json

from brigade.errors import BrigadeError
from brigade.system.client_shapes import CLIENT_REQUEST_SHAPES
from brigade.system.launch_argv_request import LaunchArgvRequest
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.resume_argv_request import ResumeArgvRequest
from brigade.system.transcripts_request import TranscriptsRequest
from brigade.system.validate_document import DocumentInvalid, validate_document

REQUEST_KINDS = {
    "launch-argv": LaunchArgvRequest,
    "resume-argv": ResumeArgvRequest,
    "parse-result": ParseResultRequest,
    "transcripts": TranscriptsRequest,
}


def read_client_request(
    operation: str, stdin: str
) -> LaunchArgvRequest | ResumeArgvRequest | ParseResultRequest | TranscriptsRequest:
    try:
        document = json.loads(stdin)
    except json.JSONDecodeError as error:
        raise BrigadeError(f"the request on stdin is not JSON: {error}") from None
    try:
        validate_document(document, CLIENT_REQUEST_SHAPES[operation])
    except DocumentInvalid as problem:
        raise BrigadeError(f"the request on stdin: {problem}") from None
    return REQUEST_KINDS[operation].from_document(document)
