from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest


def format_files(run_process: Callable[[ProcessRequest], ProcessRecord], paths: tuple[Path, ...]) -> None:
    run_awawa(run_process, paths[0].parent, ("fmt", *(str(path) for path in paths)), SUCCESS)
