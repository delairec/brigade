from pathlib import Path

from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY
from brigade.runtime import Runtime

REPOSITORY_KEYED_COLLECTORS = ("git-log", "git-diff-stat", "worktrees", "corpus")
LEDGER_KEYED_COLLECTOR = "ledger"
HEAD = "HEAD"
LEDGER_FILE_PATTERN = "*.jsonl"


def _measure_ledger(state_root: Path) -> int:
    return sum(path.stat().st_size for path in (state_root / LEDGER_DIRECTORY).glob(LEDGER_FILE_PATTERN))


def read_cache_input(name: str, project: Path, runtime: Runtime) -> str | int | None:
    if name in REPOSITORY_KEYED_COLLECTORS:
        return resolve_commit(runtime.run_process, project, HEAD)
    if name == LEDGER_KEYED_COLLECTOR:
        return _measure_ledger(runtime.paths.state_root)
    return None
