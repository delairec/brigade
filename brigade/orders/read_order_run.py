import json

from brigade.errors import BrigadeError
from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.recipes.run_order import OrderRun
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime


def read_order_run(runtime: Runtime, run_id: str) -> OrderRun:
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / run_id
    try:
        record = json.loads((run_directory / ORDER_RECORD_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BrigadeError(f"{run_id} is not a run of an order") from None
    return OrderRun(
        order=record["order"]["name"],
        project=record["order"]["project"],
        recipe=record["recipe"],
        run_id=run_id,
        run_directory=run_directory,
    )
