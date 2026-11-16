from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.format_files import format_files
from brigade.corpus.lint_corpus import lint_corpus
from brigade.errors import CorpusLintFailed
from brigade.git.restore_files import restore_files
from brigade.system.create_directory import create_directory
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.write_text_file import write_text_file


@dataclass(frozen=True)
class CorpusWrite:
    repository: Path
    workspace: Path
    file_names: tuple[str, ...]
    texts: tuple[str, ...]


def write_corpus_files(run_process: Callable[[ProcessRequest], ProcessRecord], write: CorpusWrite) -> None:
    paths = tuple(write.repository / file_name for file_name in write.file_names)
    for path, text in zip(paths, write.texts, strict=True):
        create_directory(path.parent)
        write_text_file(path, text)
    format_files(run_process, paths)
    report = lint_corpus(run_process, write.repository / write.workspace)
    if not report.clean:
        restore_files(run_process, write.repository, write.file_names)
        raise CorpusLintFailed(f"awawa lint --strict refused the change; the corpus is restored\n{report.output}")
