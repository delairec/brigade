from dataclasses import dataclass

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.collecting.read_stale_branches import read_stale_branches
from brigade.git.list_local_branches import list_local_branches
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.is_run_live_on import is_run_live_on
from brigade.runtime import Runtime

NAME = "stale-worktrees"
STALE_BRANCH = "stale branch"
MISSING_BRANCH = "missing branch"
DETACHED_WITHOUT_LIVE_RUN = "detached with no live run"
FRESH_AT_EACH_CALL = False


@dataclass(frozen=True)
class _Branches:
    local: tuple[str, ...]
    stale: tuple[str, ...]


def _find_reason(worktree: Worktree, branches: _Branches, runtime: Runtime) -> str | None:
    if worktree.branch in branches.stale:
        return STALE_BRANCH
    if worktree.branch is not None and worktree.branch not in branches.local:
        return MISSING_BRANCH
    if worktree.detached and not is_run_live_on(runtime.paths.state_root, worktree.path, is_recorded_process_alive):
        return DETACHED_WITHOUT_LIVE_RUN
    return None


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    _main_checkout, *linked = list_worktrees(runtime.run_process, inputs.project)
    branches = _Branches(
        local=list_local_branches(runtime.run_process, inputs.project),
        stale=tuple(stale["branch"] for stale in read_stale_branches(project, equipment, runtime)),
    )
    reasons = ((worktree, _find_reason(worktree, branches, runtime)) for worktree in linked)
    items = [
        {
            "path": str(worktree.path),
            "branch": worktree.branch,
            "head": worktree.head,
            "reason": reason,
            "fingerprint": str(worktree.path),
        }
        for worktree, reason in reasons
        if reason is not None
    ]
    return {**describe_collection(NAME, runtime, {"worktrees": len(items)}, items), "cache": FRESH_AT_EACH_CALL}
