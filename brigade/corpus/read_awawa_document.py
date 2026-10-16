import json
from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0


def read_awawa_document(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, arguments: tuple[str, ...]
) -> dict:
    record = run_process(
        ProcessRequest(argv=("awawa", *arguments, "--json", str(root)), cwd=str(root), timeout_s=AWAWA_TIMEOUT_S)
    )
    return json.loads(record.stdout)
