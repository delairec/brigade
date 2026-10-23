from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "reply_review_thread"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ThreadReply:
    repository: str
    thread: str
    body: str
    environment: dict


def ask_thread_reply(forge: object, forge_name: str, reply: ThreadReply, runtime: Runtime) -> None:
    answer = forge.reply_review_thread(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": reply.repository,
            "thread": reply.thread,
            "body": reply.body,
            "environment": reply.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
