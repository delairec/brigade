from brigade.corpus.append_entity_block import append_entity_block
from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.ledger.format_instant import format_instant
from brigade.runtime import Runtime
from brigade.waves.name_next_request import name_next_request
from brigade.waves.render_request_block import NewRequest, render_request_block

REQUESTS_FILE = "requests.awawa"

__all__ = ("REQUESTS_FILE", "NewRequest", "record_request")


def record_request(runtime: Runtime, new_request: NewRequest) -> str:
    root = runtime.paths.config_root
    names = []

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        name = name_next_request(texts[0], new_request.project)
        names.append(name)
        block = render_request_block(name, new_request, format_instant(runtime.now))
        return (append_entity_block(texts[0], block),)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(REQUESTS_FILE,),
            describe_message=lambda: f"brigade request new: @REQUEST.{names[0]} of @PROJECT.{new_request.project}",
            rewrite=rewrite,
        ),
    )
    return names[0]
