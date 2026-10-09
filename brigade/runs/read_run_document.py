import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.validate_document import DocumentInvalid, validate_document


def read_run_document(path: Path, kind_name: str, shape: dict) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise BrigadeError(f"{path} is not a {kind_name}: not a JSON document") from None
    try:
        validate_document(document, shape)
    except DocumentInvalid as problem:
        raise BrigadeError(f"{path} is not a {kind_name}: {problem}") from None
    return document
