from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.set_entity_status import set_entity_status
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.studies.read_study import read_study
from brigade.studies.record_study import STUDIES_FILE

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "STUDY"
ARCHIVED_STATUS = "archived"
ACTIONS = {"paused": "pause", "active": "resume"}


def _build_rewrite(runtime: Runtime, name: str, status: str):
    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...] | None:
        current = read_study(runtime, name).status
        if current == ARCHIVED_STATUS:
            raise BrigadeError(f"@{ENTITY_TYPE}.{name} is archived; it is neither paused nor resumed")
        if current == status:
            return None
        rewritten = set_entity_status(texts[0], ENTITY_TYPE, name, status)
        if rewritten is None:
            raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not written in {STUDIES_FILE}")
        return (rewritten,)

    return rewrite


def change_study_status(runtime: Runtime, name: str, status: str) -> dict:
    root = runtime.paths.config_root
    changed = change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(STUDIES_FILE,),
            describe_message=lambda: f"brigade study {ACTIONS[status]}: {name}",
            rewrite=_build_rewrite(runtime, name, status),
        ),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "study": name, "status": status, "changed": changed}
