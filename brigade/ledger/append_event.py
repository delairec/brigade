from datetime import datetime

from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.ledger_locations import LOCK_FILE
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
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.ledger.write_event_line import write_event_line
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths


def append_event(
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
    | WavePaused
    | WaveResumed
    | TaskPreflighted
    | TaskVerdict,
) -> dict:
    with hold_lock(paths.lock_directory / LOCK_FILE):
        return write_event_line(paths, instant, event)
