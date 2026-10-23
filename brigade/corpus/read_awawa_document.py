import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_awawa_document(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, arguments: tuple[str, ...]
) -> dict:
    record = run_awawa(run_process, root, (*arguments, "--json", str(root)), SUCCESS)
    return json.loads(record.stdout)
