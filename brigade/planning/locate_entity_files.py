import json
from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0


def locate_entity_files(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> dict[str, str]:
    record = run_process(
        ProcessRequest(argv=("awawa", "status", "--json", str(root)), cwd=str(root), timeout_s=AWAWA_TIMEOUT_S)
    )
    files = {}
    for entity in json.loads(record.stdout)["entities"]:
        files.setdefault(entity["type"], (root / entity["file"]).resolve().relative_to(root.resolve()).as_posix())
    return files
