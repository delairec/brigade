from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

PACKAGE_DEPTH = "2"


def read_entity_package(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, target: str) -> str:
    record = run_awawa(
        run_process, root, ("context", target, "--depth", PACKAGE_DEPTH, "--skip", "reasoning", str(root)), SUCCESS
    )
    return record.stdout
