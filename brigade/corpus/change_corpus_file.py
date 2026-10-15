from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.format_files import format_files
from brigade.corpus.lint_corpus import lint_corpus
from brigade.errors import CannotWrite, CorpusLintFailed
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.restore_files import restore_files
from brigade.system.hold_lock import hold_lock
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class CorpusChange:
    repository: Path
    lock: Path
    file_names: tuple[str, ...]
    describe_message: Callable[[], str]
    rewrite: Callable[[tuple[str, ...]], tuple[str, ...] | None]


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


def _write_checked(
    run_process: Callable[[ProcessRequest], ProcessRecord], change: CorpusChange, texts: tuple[str, ...]
) -> None:
    paths = tuple(change.repository / file_name for file_name in change.file_names)
    for path, text in zip(paths, texts, strict=True):
        _write_text(path, text)
    format_files(run_process, paths)
    report = lint_corpus(run_process, change.repository)
    if not report.clean:
        restore_files(run_process, change.repository, change.file_names)
        raise CorpusLintFailed(f"awawa lint --strict refused the change; the corpus is restored\n{report.output}")
    commit_files(
        run_process,
        CommitRequest(repository=change.repository, files=change.file_names, message=change.describe_message()),
    )


def change_corpus_file(run_process: Callable[[ProcessRequest], ProcessRecord], change: CorpusChange) -> bool:
    with hold_lock(change.lock):
        texts = change.rewrite(tuple(_read_text(change.repository / file_name) for file_name in change.file_names))
        if texts is None:
            return False
        _write_checked(run_process, change, texts)
        return True
