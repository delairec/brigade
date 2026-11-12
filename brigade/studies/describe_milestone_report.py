from brigade.studies.convert_study import Study
from brigade.studies.milestone_report_order import MilestoneReportOrder

NAME = "milestone-report"
REPORT_SLOT = "report"
ANSWER_TYPE = "REPORT"
ACTIVE = "active"
TASK_REFERENCE_PREFIX = "@TASK."
ENTITY_SEPARATOR = ","
PULL_REQUEST_COLLECTORS = {True: ("pr-list state=all",), False: ()}


def describe_milestone_report(order: MilestoneReportOrder) -> Study:
    tasks = ENTITY_SEPARATOR.join(f"{TASK_REFERENCE_PREFIX}{task}" for task in order.tasks)
    return Study(
        name=NAME,
        project=order.project,
        question=(
            f"Complete the report of the milestone {order.milestone}: what happened, why each parked or failed task"
            " stopped, how a tester checks each manual test, and which changes are worth reading by sampling."
        ),
        collectors=(
            *(f"ledger wave={wave}" for wave in order.waves),
            *PULL_REQUEST_COLLECTORS[order.reads_pull_requests],
            f"corpus ref={order.branch} entities={tasks}",
            f"git-diff-stat to={order.branch}",
        ),
        slot=REPORT_SLOT,
        every=None,
        output=f"entity:{ANSWER_TYPE}",
        answer_type=ANSWER_TYPE,
        status=ACTIVE,
        milestone=order,
    )
