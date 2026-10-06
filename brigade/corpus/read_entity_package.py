from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
PACKAGE_DEPTH = "2"


def read_entity_package(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, target: str) -> str:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "context", target, "--depth", PACKAGE_DEPTH, "--skip", "reasoning", str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
        )
    )
    return record.stdout
