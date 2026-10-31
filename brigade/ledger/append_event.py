from datetime import datetime

from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.inbox_dismissed import InboxDismissed
from brigade.ledger.inbox_recorded import InboxRecorded
from brigade.ledger.ledger_locations import LOCK_FILE
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_created import MilestoneCreated
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_promoted import TaskPromoted
from brigade.ledger.task_review_answered import TaskReviewAnswered
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.tick_action_failed import TickActionFailed
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_merged import WaveMerged
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.ledger.write_event_line import write_event_line
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths

AppendedEvent = (
    RunFinished
    | SignalRecorded
    | ForgeAccountUnavailable
    | PlanLintFailed
    | WaveStarted
    | TaskState
    | TaskParked
    | OrderStarted
    | StepDone
    | StepFailed
    | OrderParked
    | OrderDone
    | TaskPrOpened
    | MilestoneCreated
    | MilestoneBranchCut
    | MilestonePrOpened
    | MilestoneClosed
    | TaskPromoted
    | WavePaused
    | WaveResumed
    | TaskPreflighted
    | TaskVerdict
    | TaskReviewAnswered
    | WaveReported
    | WaveClosed
    | WaveMerged
    | WavePrOpened
    | TickActionFailed
    | InboxRecorded
    | InboxDismissed
)


def append_event(paths: Paths, instant: datetime, event: AppendedEvent) -> dict:
    with hold_lock(paths.lock_directory / LOCK_FILE):
        return write_event_line(paths, instant, event)
