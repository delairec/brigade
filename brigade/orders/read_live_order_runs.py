import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from brigade.orders.live_order_run import LiveOrderRun
from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.runs.run_locations import RUNS_DIRECTORY


def _read_live_order_run(record: Path) -> LiveOrderRun:
    document = json.loads(record.read_text(encoding="utf-8"))
    return LiveOrderRun(
        order=document["order"]["name"],
        recipe=document["recipe"]["name"],
        run=record.parent.name,
        started=datetime.fromtimestamp(record.stat().st_mtime, UTC),
        max_wall=document["recipe"]["max_wall"],
    )


def read_live_order_runs(state_root: Path, is_alive: Callable[[Path], bool]) -> tuple[LiveOrderRun, ...]:
    return tuple(
        _read_live_order_run(record)
        for record in sorted((state_root / RUNS_DIRECTORY).glob(f"*/{ORDER_RECORD_FILE}"))
        if is_alive(record.parent)
    )
