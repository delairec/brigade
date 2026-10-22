from brigade.ledger.constraint_delivered import ConstraintDelivered
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.milestone_created import MilestoneCreated
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.pattern_ratified import PatternRatified
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.pr_merged import PrMerged
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
from brigade.ledger.undeclared_event import UndeclaredEvent
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted

LEDGER_SCHEMA_VERSION = 1
RUN_FINISHED_SCHEMA_VERSION = 2
WAVE_STARTED_SCHEMA_VERSION = 2
WRITTEN_SCHEMA_VERSIONS = {
    RunFinished.name: RUN_FINISHED_SCHEMA_VERSION,
    WaveStarted.name: WAVE_STARTED_SCHEMA_VERSION,
}
DECLARED_EVENTS = {
    kind.name: kind
    for kind in (
        RunFinished,
        WaveStarted,
        WavePaused,
        WaveResumed,
        WaveReported,
        WaveClosed,
        WaveCancelled,
        TaskParked,
        TaskState,
        PrMerged,
        OrderStarted,
        StepDone,
        StepFailed,
        OrderParked,
        OrderDone,
        SignalRecorded,
        PatternRatified,
        ConstraintDelivered,
        ForgeAccountUnavailable,
        PlanLintFailed,
        TaskPrOpened,
        MilestoneCreated,
        TaskPromoted,
        TaskPreflighted,
        TaskVerdict,
        TaskReviewAnswered,
    )
}
LedgerEvent = (
    RunFinished
    | WaveStarted
    | WavePaused
    | WaveResumed
    | WaveReported
    | WaveClosed
    | WaveCancelled
    | TaskParked
    | TaskState
    | PrMerged
    | OrderStarted
    | StepDone
    | StepFailed
    | OrderParked
    | OrderDone
    | SignalRecorded
    | PatternRatified
    | ConstraintDelivered
    | ForgeAccountUnavailable
    | PlanLintFailed
    | TaskPrOpened
    | MilestoneCreated
    | TaskPromoted
    | TaskPreflighted
    | TaskVerdict
    | TaskReviewAnswered
    | UndeclaredEvent
)
