from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.write_text_file import write_text_file

NO_ENTITIES = None
SCHEMA_VERSION = 1


def _read_file(request: dict) -> str:
    return Path(request["path"]).read_text(encoding="utf-8")


def create_document(request: dict, runtime: Runtime) -> dict:
    write_text_file(Path(request["path"]), "")
    return {"schema_version": SCHEMA_VERSION}


def describe_document(request: dict, runtime: Runtime) -> dict:
    frame = "".join(f"- {line}\n" for line in request["frame"])
    return {
        "schema_version": SCHEMA_VERSION,
        "text": f"The {request['document']} is the Markdown file {request['path']}.\n\n{frame}",
    }


def read_document(request: dict, runtime: Runtime) -> dict:
    return {"schema_version": SCHEMA_VERSION, "text": _read_file(request)}


def detect_entry(request: dict, runtime: Runtime) -> dict:
    return {"schema_version": SCHEMA_VERSION, "holds_entry": bool(_read_file(request).strip())}


def render_document(request: dict, runtime: Runtime) -> dict:
    return {"schema_version": SCHEMA_VERSION, "text": _read_file(request), "entities": NO_ENTITIES}
