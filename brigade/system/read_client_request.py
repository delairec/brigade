import json

from brigade.errors import BrigadeError
from brigade.system.client_shapes import CLIENT_REQUEST_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document


def read_client_request(operation: str, stdin: str) -> dict:
    try:
        document = json.loads(stdin)
    except json.JSONDecodeError as error:
        raise BrigadeError(f"the request on stdin is not JSON: {error}") from None
    try:
        validate_document(document, CLIENT_REQUEST_SHAPES[operation])
    except DocumentInvalid as problem:
        raise BrigadeError(f"the request on stdin: {problem}") from None
    return document
