from brigade.corpus.read_entities import Entity
from brigade.ledger.task_branch_cut import TaskBranchCut
from brigade.tick.name_branch_of_task import name_branch_of_task


def read_branch_of_task(events: tuple, project: str, task: Entity) -> str:
    cuts = [
        event.branch
        for event in events
        if isinstance(event, TaskBranchCut) and event.project == project and event.task == task.name
    ]
    return cuts[-1] if cuts else name_branch_of_task(task)
