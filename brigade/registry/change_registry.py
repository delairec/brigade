from collections.abc import Callable

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.runtime import Runtime

REGISTRY_FILE = "projects.awawa"


def change_registry(runtime: Runtime, message: str, rewrite: Callable[[str], str | None]) -> bool:
    return change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=runtime.paths.config_root,
            lock_directory=runtime.paths.lock_directory,
            file_name=REGISTRY_FILE,
            message=message,
            rewrite=rewrite,
        ),
    )
