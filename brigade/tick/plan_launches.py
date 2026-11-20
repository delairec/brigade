from collections.abc import Iterable
from dataclasses import dataclass

from brigade.ledger.task_state import HANDOVER_RESUME_REASON
from brigade.tick.actions import LaunchTask, ResumeTaskRun
from brigade.tick.build_snapshot import ProjectFacts, Snapshot, TaskFacts, WaveFacts
from brigade.tick.find_launch_hold import LaunchRound, find_launch_holds
from brigade.tick.head_proof import ForgeCheck, HeadChecks
from brigade.waves.read_task_state import PARKED_STATE
from brigade.waves.read_wave_pause import WavePause

BUILD_SLOT = "build"
WAITING_STATE = "queued"
RUNNING_STATE = "running"
OPEN_PULL_REQUEST = "open"
STARTING_STATES = (WAITING_STATE, PARKED_STATE)


@dataclass(frozen=True)
class HeldTask:
    project: str
    wave: str
    task: str
    cause: str

    def to_document(self) -> dict:
        return {"project": self.project, "wave": self.wave, "task": self.task, "cause": self.cause}


@dataclass(frozen=True)
class LaunchPlan:
    launches: tuple
    held: tuple[HeldTask, ...]


def _count_used_slots(project: ProjectFacts) -> int:
    return sum(1 for live in project.live_runs if live.slot == BUILD_SLOT)


def _read_open_pull_request_checks(task: TaskFacts) -> HeadChecks | None:
    if task.pull_request is None or task.pull_request.state != OPEN_PULL_REQUEST:
        return None
    return HeadChecks(
        head=task.pull_request.head,
        checks=tuple(ForgeCheck(name=check.name, conclusion=check.conclusion) for check in task.pull_request.checks),
    )


def _decide_launch(wave: WaveFacts, task: TaskFacts) -> LaunchTask | ResumeTaskRun:
    if task.handed_over_run is not None:
        return ResumeTaskRun(
            wave=wave.wave,
            task=task.name,
            run=task.handed_over_run.run,
            state=RUNNING_STATE,
            reason=HANDOVER_RESUME_REASON,
            slot=task.handed_over_run.slot,
        )
    return LaunchTask(
        project=wave.project,
        wave=wave.wave,
        branch=wave.base,
        task=task.name,
        task_branch=task.branch,
        pull_request_checks=_read_open_pull_request_checks(task),
    )


def _is_starting(task: TaskFacts, wave: WaveFacts) -> bool:
    return wave.states.get(task.name, WAITING_STATE) in STARTING_STATES and task.name not in wave.implemented


def _is_relaunched(task: TaskFacts, wave: WaveFacts, live_tasks: frozenset) -> bool:
    return (
        wave.states.get(task.name) == RUNNING_STATE
        and (task.rebased_by_last_run or task.stopped_by_login)
        and (wave.wave, task.name) not in live_tasks
    )


@dataclass(frozen=True)
class ProjectRound:
    slots: int
    used_slots: int


@dataclass(frozen=True)
class RoundHold:
    wave: WaveFacts
    task: TaskFacts
    hold: str | None


def find_round_holds(
    waves: Iterable[WaveFacts],
    projects: dict[str, ProjectRound],
    halts: dict[str, WavePause],
    live_tasks: frozenset,
) -> tuple[RoundHold, ...]:
    used_slots = {name: project.used_slots for name, project in projects.items()}
    holds = []
    for wave in waves:
        launch_round = LaunchRound(
            halt=halts.get(wave.wave), used_slots=used_slots[wave.project], slots=projects[wave.project].slots
        )
        candidates = (task for task in wave.tasks if _is_starting(task, wave) or _is_relaunched(task, wave, live_tasks))
        for task, hold in find_launch_holds(candidates, wave, launch_round):
            if hold is None:
                used_slots[wave.project] += 1
            holds.append(RoundHold(wave=wave, task=task, hold=hold))
    return tuple(holds)


def plan_launches(snapshot: Snapshot, halts: dict[str, WavePause]) -> LaunchPlan:
    projects = {
        project.name: ProjectRound(slots=project.slots, used_slots=_count_used_slots(project))
        for project in snapshot.projects
    }
    live_tasks = frozenset((live.wave, live.task) for project in snapshot.projects for live in project.live_runs)
    launches = []
    held = []
    for round_hold in find_round_holds(snapshot.waves, projects, halts, live_tasks):
        wave, task = round_hold.wave, round_hold.task
        if round_hold.hold is None:
            launches.append(_decide_launch(wave, task))
        elif _is_starting(task, wave):
            held.append(HeldTask(project=wave.project, wave=wave.wave, task=task.name, cause=round_hold.hold))
    return LaunchPlan(launches=tuple(launches), held=tuple(held))
