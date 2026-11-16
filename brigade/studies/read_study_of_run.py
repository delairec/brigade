import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.runtime import Runtime
from brigade.studies.describe_milestone_report import describe_milestone_report
from brigade.studies.describe_study_order import PARAM_SEPARATOR
from brigade.studies.describe_task_report import describe_task_report
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.read_study import Study, read_study
from brigade.studies.task_report_order import TaskReportOrder

MILESTONE_KEY = "milestone"
TASK_KEY = "task"


def _read_milestone_report_order(recorded: dict) -> MilestoneReportOrder:
    return MilestoneReportOrder(
        project=recorded["project"],
        milestone=recorded["milestone"],
        branch=recorded["branch"],
        waves=tuple(recorded["waves"]),
        tasks=tuple(recorded["tasks"]),
        reads_pull_requests=recorded.get("reads_pull_requests", True),
    )


def _read_arguments(order: dict) -> dict:
    return {key: json.loads(value) for key, _, value in (param.partition(PARAM_SEPARATOR) for param in order["params"])}


def read_study_of_run(runtime: Runtime, run_directory: Path) -> Study:
    try:
        order = json.loads((run_directory / ORDER_RECORD_FILE).read_text(encoding="utf-8"))["order"]
    except FileNotFoundError:
        raise BrigadeError(f"{run_directory.name} is not a run of a study") from None
    arguments = _read_arguments(order)
    if TASK_KEY in arguments:
        return describe_task_report(TaskReportOrder(**arguments[TASK_KEY]))
    if MILESTONE_KEY in arguments:
        return describe_milestone_report(_read_milestone_report_order(arguments[MILESTONE_KEY]))
    return read_study(runtime, order["name"])
