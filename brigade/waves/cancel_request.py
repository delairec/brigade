from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.set_entity_status import set_entity_status
from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.waves.read_wave_request import ENTITY_TYPE, read_wave_request
from brigade.waves.record_request import REQUESTS_FILE

CANCELLED_STATUS = "cancelled"
CANCELLABLE_STATUSES = ("planning", "planned")


def _build_rewrite(runtime: Runtime, name: str):
    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        status = read_project_field(read_wave_request(runtime, name), "STATUS")
        if status not in CANCELLABLE_STATUSES:
            raise BrigadeError(f"@{ENTITY_TYPE}.{name} is {status}")
        return (set_entity_status(texts[0], ENTITY_TYPE, name, CANCELLED_STATUS),)

    return rewrite


def cancel_request(runtime: Runtime, name: str) -> str:
    require_operational_corpus(runtime.paths)
    root = runtime.paths.config_root
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(REQUESTS_FILE,),
            describe_message=lambda: f"brigade request cancel: @{ENTITY_TYPE}.{name} {CANCELLED_STATUS}",
            rewrite=_build_rewrite(runtime, name),
        ),
    )
    return CANCELLED_STATUS
