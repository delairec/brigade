from pathlib import Path

LOCK_PREFIX = "corpus-"
LOCK_SUFFIX = ".lock"


def locate_corpus_lock(lock_directory: Path, repository: Path) -> Path:
    key = str(repository).lstrip("/").replace("/", "-")
    return lock_directory / f"{LOCK_PREFIX}{key}{LOCK_SUFFIX}"
