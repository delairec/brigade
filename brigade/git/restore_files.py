from pathlib import Path
from typing import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0


def _run_git(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, *arguments: str) -> str:
    record = run_process(ProcessRequest(argv=("git", *arguments), cwd=str(repository), timeout_s=GIT_TIMEOUT_S))
    return record.stdout


def restore_files(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, files: tuple[str, ...]
) -> None:
    held = set(_run_git(run_process, repository, "ls-tree", "--name-only", "HEAD", "--", *files).splitlines())
    held_files = tuple(file for file in files if file in held)
    new_files = tuple(file for file in files if file not in held)
    if held_files:
        _run_git(run_process, repository, "checkout", "HEAD", "--", *held_files)
    if new_files:
        _run_git(run_process, repository, "rm", "--cached", "--quiet", "--ignore-unmatch", "--", *new_files)
        _run_git(run_process, repository, "clean", "--force", "--quiet", "--", *new_files)
