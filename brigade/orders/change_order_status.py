from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.read_entity import read_entity
from brigade.corpus.set_entity_status import set_entity_status
from brigade.errors import BrigadeError
from brigade.orders.record_order import ORDERS_FILE
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "ORDER"
ARCHIVED_STATUS = "archived"
ACTIONS = {"paused": "pause", "active": "resume", ARCHIVED_STATUS: "cancel"}


def _read_status(runtime: Runtime, name: str) -> str:
    entity = read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name)
    return next(field.value for field in entity.fields if field.name == "STATUS")


def _build_rewrite(runtime: Runtime, name: str, status: str):
    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...] | None:
        current = _read_status(runtime, name)
        if current == status:
            return None
        if current == ARCHIVED_STATUS:
            raise BrigadeError(f"@{ENTITY_TYPE}.{name} is archived; its status no longer changes")
        return (set_entity_status(texts[0], ENTITY_TYPE, name, status),)

    return rewrite


def change_order_status(runtime: Runtime, name: str, status: str) -> dict:
    root = runtime.paths.config_root
    changed = change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(ORDERS_FILE,),
            describe_message=lambda: f"brigade order {ACTIONS[status]}: {name}",
            rewrite=_build_rewrite(runtime, name, status),
        ),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "order": name, "status": status, "changed": changed}
