import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_awawa_file_document(
    run_process: Callable[[ProcessRequest], ProcessRecord], file: Path, arguments: tuple[str, ...]
) -> dict:
    record = run_awawa(run_process, file.parent, (*arguments, "--json", str(file)), SUCCESS)
    return json.loads(record.stdout)
