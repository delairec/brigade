import json
from pathlib import Path
from typing import Optional

from brigade.errors import BrigadeError
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

HEARTBEAT_SHAPE = {
    "schema_version": Field(kinds=(int,), values=(1,)),
    "ts": Field(kinds=(str,)),
    "duration_ms": Field(kinds=(int,)),
    "actions_applied": Field(kinds=(int,)),
}


def read_heartbeat(path: Path) -> Optional[dict]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        document = json.loads(content)
    except ValueError:
        raise BrigadeError(f"{path} is not a heartbeat: not a JSON document") from None
    try:
        validate_document(document, HEARTBEAT_SHAPE)
    except DocumentInvalid as problem:
        raise BrigadeError(f"{path} is not a heartbeat: {problem}") from None
    return document
