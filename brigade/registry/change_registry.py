from typing import Callable, Optional

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file

REGISTRY_FILE = "projects.awawa"
LOCK_DIRECTORY = "locks"


def change_registry(runtime, message: str, rewrite: Callable[[str], Optional[str]]) -> bool:
    return change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=runtime.paths.config_root,
            lock_directory=runtime.paths.state_root / LOCK_DIRECTORY,
            file_name=REGISTRY_FILE,
            message=message,
            rewrite=rewrite,
        ),
    )
