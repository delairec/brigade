from brigade.studies.convert_study import Study
from brigade.studies.task_report_order import TaskReportOrder

NAME = "task-report"
REPORT_SLOT = "report"
ANSWER_TYPE = "REPORT"
ACTIVE = "active"
TASK_REFERENCE_PREFIX = "@TASK."


def describe_task_report(order: TaskReportOrder) -> Study:
    return Study(
        name=NAME,
        project=order.project,
        question=(
            f"Complete the report of the task {order.task}: what happened, why it stopped if parked or failed,"
            " how a tester checks each manual test, and which changes are worth reading by sampling."
        ),
        collectors=(
            f"ledger wave={order.wave}",
            "pr-list state=all",
            f"corpus ref={order.branch} entities={TASK_REFERENCE_PREFIX}{order.task}",
            f"git-diff-stat to={order.branch}",
        ),
        slot=REPORT_SLOT,
        every=None,
        output=f"entity:{ANSWER_TYPE}",
        answer_type=ANSWER_TYPE,
        status=ACTIVE,
        task=order,
    )
