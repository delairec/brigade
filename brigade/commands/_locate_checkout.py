from pathlib import Path

from brigade.git.detect_repository import detect_repository
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.runtime import Runtime


def locate_checkout(runtime: Runtime) -> Path:
    directory = Path.cwd()
    if not detect_repository(runtime.run_process, directory):
        return directory
    return locate_main_checkout(runtime.run_process, locate_worktree_root(runtime.run_process, directory))
