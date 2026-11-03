from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_corpus_types(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> list[str]:
    status = read_awawa_document(run_process, root, ("status",))
    return [row["type"] for row in status["types"]]
