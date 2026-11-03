import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.studies.describe_milestone_report import describe_milestone_report
from brigade.studies.describe_task_report import describe_task_report
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.read_study import Study, read_study
from brigade.studies.study_run_context import STUDY_RECORD_FILE
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
    )


def read_study_of_run(runtime: Runtime, run_directory: Path) -> Study:
    try:
        record = json.loads((run_directory / STUDY_RECORD_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BrigadeError(f"{run_directory.name} is not a run of a study") from None
    if record.get(TASK_KEY) is not None:
        return describe_task_report(TaskReportOrder(**record[TASK_KEY]))
    if record.get(MILESTONE_KEY) is not None:
        return describe_milestone_report(_read_milestone_report_order(record[MILESTONE_KEY]))
    return read_study(runtime, record["study"])
