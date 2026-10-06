from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.format_files import format_files
from brigade.corpus.lint_corpus import lint_corpus
from brigade.errors import BrigadeError, CannotWrite
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.restore_files import restore_files
from brigade.system.hold_lock import hold_lock
from brigade.system.run_process import ProcessRecord, ProcessRequest

LOCK_PREFIX = "corpus-"
LOCK_SUFFIX = ".lock"


@dataclass(frozen=True)
class CorpusChange:
    repository: Path
    lock_directory: Path
    file_name: str
    message: str
    rewrite: Callable[[str], str | None]


def _locate_lock(change: CorpusChange) -> Path:
    key = str(change.repository).lstrip("/").replace("/", "-")
    return change.lock_directory / f"{LOCK_PREFIX}{key}{LOCK_SUFFIX}"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_checked(run_process: Callable[[ProcessRequest], ProcessRecord], change: CorpusChange, text: str) -> None:
    path = change.repository / change.file_name
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
    format_files(run_process, (path,))
    report = lint_corpus(run_process, change.repository)
    if not report.clean:
        restore_files(run_process, change.repository, (change.file_name,))
        raise BrigadeError(f"awawa lint --strict refused the change; the corpus is restored\n{report.output}")
    commit_files(
        run_process, CommitRequest(repository=change.repository, files=(change.file_name,), message=change.message)
    )


def change_corpus_file(run_process: Callable[[ProcessRequest], ProcessRecord], change: CorpusChange) -> bool:
    with hold_lock(_locate_lock(change)):
        text = change.rewrite(_read_text(change.repository / change.file_name))
        if text is None:
            return False
        _write_checked(run_process, change, text)
        return True
