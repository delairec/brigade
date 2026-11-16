from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.recipes.lint_recipe import ON_FAIL_KEY, PARK
from brigade.runtime import Runtime
from brigade.system.write_json_atomically import write_json_atomically

STEPS_DIRECTORY = "steps"
FIRST_STEP = 1
DONE = "done"
PARKED = "parked"
STOPPED = "stopped"
SKIP = "skip"
STOP = "stop"
RETRY_PREFIX = "retry:"
NO_RETRY = 0


@dataclass(frozen=True)
class OrderRun:
    order: str
    project: str | None
    recipe: dict
    run_id: str
    run_directory: Path


StepPerformer = Callable[[dict, OrderRun], dict]


@dataclass(frozen=True)
class _RankedStep:
    name: str
    step: dict
    perform: StepPerformer


class _StepFailure(Exception):
    def __init__(self, step: str, reason: str, on_fail: str):
        super().__init__(reason)
        self.step = step
        self.reason = reason
        self.on_fail = on_fail


def _count_retries(on_fail: str) -> int:
    if on_fail.startswith(RETRY_PREFIX):
        return int(on_fail.removeprefix(RETRY_PREFIX))
    return NO_RETRY


def _perform(runtime: Runtime, run: OrderRun, ranked: _RankedStep) -> dict:
    name = ranked.name
    on_fail = ranked.step.get(ON_FAIL_KEY, PARK)
    attempts_left = _count_retries(on_fail)
    while True:
        try:
            return ranked.perform(ranked.step, run)
        except BrigadeError as error:
            reason = str(error)
            append_event(
                runtime.paths,
                runtime.now,
                StepFailed(kind=run.recipe["name"], run=run.run_id, step=name, reason=reason),
            )
            if attempts_left == NO_RETRY:
                raise _StepFailure(name, reason, on_fail) from None
            attempts_left -= 1


def _check_wall(runtime: Runtime, run: OrderRun, name: str) -> None:
    max_wall = run.recipe["max_wall"]
    if runtime.read_clock() - runtime.now > timedelta(minutes=max_wall):
        raise _StepFailure(
            name, f"the run passed the max_wall of {max_wall} minutes of the recipe {run.recipe['name']}", PARK
        )


def _end(runtime: Runtime, run: OrderRun) -> None:
    append_event(
        runtime.paths,
        runtime.now,
        OrderDone(project=run.project, kind=run.recipe["name"], order=run.order, run=run.run_id),
    )


def _park(runtime: Runtime, run: OrderRun, failure: _StepFailure) -> dict:
    append_event(
        runtime.paths,
        runtime.now,
        OrderParked(
            project=run.project,
            kind=run.recipe["name"],
            order=run.order,
            run=run.run_id,
            step=failure.step,
            reason=failure.reason,
        ),
    )
    return {"order": run.order, "run": run.run_id, "state": PARKED, "step": failure.step, "reason": failure.reason}


def _run_steps(runtime: Runtime, run: OrderRun, performers: Mapping[str, StepPerformer]) -> None:
    for rank, step in enumerate(run.recipe["steps"], start=FIRST_STEP):
        name = f"{rank}-{step['kind']}"
        result_path = run.run_directory / STEPS_DIRECTORY / f"{name}.json"
        if result_path.is_file():
            continue
        _check_wall(runtime, run, name)
        try:
            result = _perform(runtime, run, _RankedStep(name=name, step=step, perform=performers[step["kind"]]))
        except _StepFailure as failure:
            if failure.on_fail != SKIP:
                raise
            result = {"skipped": failure.reason}
        else:
            append_event(runtime.paths, runtime.now, StepDone(kind=run.recipe["name"], run=run.run_id, step=name))
        write_json_atomically(result_path, result)


def run_order(runtime: Runtime, run: OrderRun, performers: Mapping[str, StepPerformer]) -> dict:
    try:
        _run_steps(runtime, run, performers)
    except _StepFailure as failure:
        if failure.on_fail != STOP:
            return _park(runtime, run, failure)
        _end(runtime, run)
        return {"order": run.order, "run": run.run_id, "state": STOPPED, "step": failure.step, "reason": failure.reason}
    _end(runtime, run)
    return {"order": run.order, "run": run.run_id, "state": DONE}
