from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.write_corpus_files import CorpusWrite, write_corpus_files
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.system.hold_lock import hold_lock
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class CorpusChange:
    repository: Path
    lock: Path
    file_names: tuple[str, ...]
    describe_message: Callable[[], str]
    rewrite: Callable[[tuple[str, ...]], tuple[str, ...] | None]
    workspace: Path = Path()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_checked(
    run_process: Callable[[ProcessRequest], ProcessRecord], change: CorpusChange, texts: tuple[str, ...]
) -> None:
    write_corpus_files(
        run_process,
        CorpusWrite(
            repository=change.repository, workspace=change.workspace, file_names=change.file_names, texts=texts
        ),
    )
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
