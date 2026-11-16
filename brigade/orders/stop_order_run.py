import signal
from collections.abc import Callable

from brigade.ledger.order_parked import OrderParked
from brigade.orders.park_order import park_order
from brigade.orders.read_order_run import read_order_run
from brigade.recipes.run_order import FIRST_STEP, STEPS_DIRECTORY, OrderRun
from brigade.runs.read_run_pid import read_run_pid
from brigade.runtime import Runtime
from brigade.tick.actions import StopOrderRun


def _find_first_undone_step(run: OrderRun) -> str:
    names = (f"{rank}-{step['kind']}" for rank, step in enumerate(run.recipe["steps"], start=FIRST_STEP))
    return next(name for name in names if not (run.run_directory / STEPS_DIRECTORY / f"{name}.json").is_file())


def stop_order_run(runtime: Runtime, action: StopOrderRun, signal_process: Callable[[int, int], None]) -> None:
    run = read_order_run(runtime, action.run)
    signal_process(read_run_pid(run.run_directory).pid, signal.SIGTERM)
    park_order(
        runtime,
        OrderParked(
            project=run.project,
            kind=run.recipe["name"],
            order=run.order,
            run=run.run_id,
            step=_find_first_undone_step(run),
            reason=action.reason,
        ),
    )
