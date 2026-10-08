import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.validate_document import DocumentInvalid, validate_document
from brigade.tick.heartbeat import HEARTBEAT_SHAPE, Heartbeat


def read_heartbeat(path: Path) -> Heartbeat | None:
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
    return Heartbeat.from_document(document)
