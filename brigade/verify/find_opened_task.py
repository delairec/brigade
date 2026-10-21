from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.runtime import Runtime


@dataclass(frozen=True)
class OpenedTask:
    opened: TaskPrOpened
    wave_branch: str


def find_opened_task(runtime: Runtime, project: str, pr: int) -> OpenedTask:
    events = [entry.event for entry in read_ledger(runtime.paths.state_root).entries]
    opened = [
        event for event in events if isinstance(event, TaskPrOpened) and (event.project, event.pr) == (project, pr)
    ]
    if not opened:
        raise BrigadeError(f"no task.pr_opened of @PROJECT.{project} names the pull request #{pr}")
    wave_branch = next(
        event.branch for event in events if isinstance(event, WaveStarted) and event.wave == opened[-1].wave
    )
    return OpenedTask(opened=opened[-1], wave_branch=wave_branch)
