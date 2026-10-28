from pathlib import Path

from brigade.runs.describe_progress import PROGRESS_DOCUMENT, PROGRESS_FRAME, PROGRESS_SCHEMA
from brigade.runtime import Runtime
from brigade.system.ask_document import DocumentQuestion, ask_document
from brigade.system.document_request import DocumentRequest
from brigade.system.name_document_plugin import name_document_plugin

NO_ROLE_SHELL = False


def _ask(document: object, operation: str, progress_file: Path, runtime: Runtime):
    request = DocumentRequest(
        document=PROGRESS_DOCUMENT,
        path=str(progress_file),
        schema=PROGRESS_SCHEMA.read_text(encoding="utf-8"),
        frame=PROGRESS_FRAME,
        role_has_shell=NO_ROLE_SHELL,
    )
    question = DocumentQuestion(document_name=name_document_plugin(progress_file), operation=operation, request=request)
    return ask_document(document, question, runtime)


def render_progress(progress_file: Path, document: object, runtime: Runtime) -> dict | None:
    if not _ask(document, "detect_entry", progress_file, runtime).holds_entry:
        return None
    rendering = _ask(document, "render_document", progress_file, runtime)
    return {"text": rendering.text, "entities": rendering.entities}
