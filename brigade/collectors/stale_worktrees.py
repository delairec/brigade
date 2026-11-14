from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.collecting.read_stale_branches import read_stale_branches
from brigade.collecting.read_stale_worktrees import StaleWorktreesReading, read_stale_worktrees
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runtime import Runtime

NAME = "stale-worktrees"
FRESH_AT_EACH_CALL = False


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    reading = StaleWorktreesReading(
        repository=inputs.project,
        stale_branches=tuple(stale["branch"] for stale in read_stale_branches(project, equipment, runtime)),
        state_root=runtime.paths.state_root,
        is_alive=is_recorded_process_alive,
    )
    items = [
        {
            "path": str(stale.worktree.path),
            "branch": stale.worktree.branch,
            "head": stale.worktree.head,
            "reason": stale.reason,
            "fingerprint": str(stale.worktree.path),
        }
        for stale in read_stale_worktrees(runtime.run_process, reading)
    ]
    return {**describe_collection(NAME, runtime, {"worktrees": len(items)}, items), "cache": FRESH_AT_EACH_CALL}
