from collections.abc import Callable

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.runtime import Runtime

REGISTRY_FILE = "projects.awawa"


def change_registry(runtime: Runtime, message: str, rewrite: Callable[[str], str | None]) -> bool:
    def rewrite_registry(texts: tuple[str, ...]) -> tuple[str, ...] | None:
        text = rewrite(texts[0])
        return None if text is None else (text,)

    return change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=runtime.paths.config_root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, runtime.paths.config_root),
            file_names=(REGISTRY_FILE,),
            describe_message=lambda: message,
            rewrite=rewrite_registry,
        ),
    )
