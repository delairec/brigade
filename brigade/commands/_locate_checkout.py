from pathlib import Path

from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.runtime import Runtime


def locate_checkout(runtime: Runtime) -> Path:
    return locate_main_checkout(runtime.run_process, locate_worktree_root(runtime.run_process, Path.cwd()))
