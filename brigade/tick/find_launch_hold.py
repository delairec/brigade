import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from brigade.tasks.read_task_number import read_task_number
from brigade.tick.build_snapshot import TaskFacts, WaveFacts
from brigade.waves.describe_wave_halt import describe_wave_halt
from brigade.waves.read_task_state import PARKED_STATE
from brigade.waves.read_wave_pause import WavePause

MERGED_STATE = "merged"
WAITING_STATE = "queued"


@dataclass(frozen=True)
class LaunchRound:
    halt: WavePause | None
    used_slots: int
    slots: int


def _find_unmet_after(task: TaskFacts, wave: WaveFacts) -> str | None:
    return next(
        (
            earlier
            for earlier in task.after
            if wave.states.get(earlier) != MERGED_STATE and earlier not in wave.implemented
        ),
        None,
    )


def _find_start_hold(task: TaskFacts, wave: WaveFacts) -> str | None:
    unmet_after = _find_unmet_after(task, wave)
    if unmet_after is not None:
        return f"after {unmet_after}"
    if task.blocked_by:
        return f"blocked by {', '.join(task.blocked_by)}"
    return None


def find_launch_hold(task: TaskFacts, wave: WaveFacts, launch_round: LaunchRound) -> str | None:
    if launch_round.halt is not None:
        return describe_wave_halt(wave.wave, launch_round.halt)
    state = wave.states.get(task.name, WAITING_STATE)
    if state == PARKED_STATE:
        return f"parked: {task.parked_reason}"
    start_hold = _find_start_hold(task, wave) if state == WAITING_STATE else None
    if start_hold is not None:
        return start_hold
    if launch_round.used_slots >= launch_round.slots:
        return f"no free build slot: {launch_round.used_slots} used of SLOTS {launch_round.slots}"
    return None


def find_launch_holds(
    tasks: Iterable[TaskFacts], wave: WaveFacts, launch_round: LaunchRound
) -> tuple[tuple[TaskFacts, str | None], ...]:
    used_slots = launch_round.used_slots
    holds = []
    for task in sorted(tasks, key=lambda task: read_task_number(task.name, wave.wave)):
        hold = find_launch_hold(task, wave, dataclasses.replace(launch_round, used_slots=used_slots))
        if hold is None:
            used_slots += 1
        holds.append((task, hold))
    return tuple(holds)
