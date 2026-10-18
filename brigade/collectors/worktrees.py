from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.git.list_worktrees import list_worktrees
from brigade.runtime import Runtime

NAME = "worktrees"


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    worktrees = list_worktrees(runtime.run_process, inputs.project)
    items = [
        {
            "path": str(worktree.path),
            "branch": worktree.branch,
            "head": worktree.head,
            "detached": worktree.detached,
            "locked": worktree.locked,
        }
        for worktree in worktrees
    ]
    return describe_collection(NAME, runtime, {"worktrees": len(worktrees)}, items)
