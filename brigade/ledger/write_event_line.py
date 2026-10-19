import json
from datetime import UTC, datetime

from brigade.errors import BrigadeError, CannotWrite
from brigade.ledger.declared_events import LEDGER_SCHEMA_VERSION, WRITTEN_SCHEMA_VERSIONS
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY
from brigade.ledger.milestone_created import MilestoneCreated
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_promoted import TaskPromoted
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.system.paths import Paths

MONTH_FILE_FORMAT = "%Y-%m.jsonl"


class LedgerEventRefused(BrigadeError):
    pass


def write_event_line(
    paths: Paths,
    instant: datetime,
    event: RunFinished
    | SignalRecorded
    | ForgeAccountUnavailable
    | PlanLintFailed
    | WaveStarted
    | TaskState
    | OrderStarted
    | StepDone
    | StepFailed
    | OrderParked
    | OrderDone
    | TaskPrOpened
    | MilestoneCreated
    | TaskPromoted
    | TaskPreflighted,
) -> dict:
    if instant.utcoffset() is None:
        raise LedgerEventRefused(f"the instant of the event {event.name} carries no time zone")
    utc_instant = instant.astimezone(UTC)
    line = {
        "schema_version": WRITTEN_SCHEMA_VERSIONS.get(event.name, LEDGER_SCHEMA_VERSION),
        "ts": format_instant(utc_instant),
        "event": event.name,
        **event.to_document(),
    }
    ledger_directory = paths.state_root / LEDGER_DIRECTORY
    month_file = ledger_directory / utc_instant.strftime(MONTH_FILE_FORMAT)
    try:
        ledger_directory.mkdir(parents=True, exist_ok=True)
        with month_file.open("a", encoding="utf-8") as ledger_file:
            ledger_file.write(json.dumps(line) + "\n")
            ledger_file.flush()
    except OSError as error:
        raise CannotWrite(error.filename or month_file, error) from error
    return line
