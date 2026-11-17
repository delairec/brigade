import dataclasses
import json

from brigade.orders.convert_order import Order
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import STUDY_KIND

NO_TEXT = None
PARAM_SEPARATOR = "="


def _describe_arguments(study: Study) -> tuple[str, ...]:
    reports = {"milestone": study.milestone, "task": study.task}
    return tuple(
        f"{key}{PARAM_SEPARATOR}{json.dumps(dataclasses.asdict(report))}"
        for key, report in reports.items()
        if report is not None
    )


def describe_study_order(study: Study) -> Order:
    return Order(
        name=study.name,
        recipe=STUDY_KIND,
        project=study.project,
        text=NO_TEXT,
        params=_describe_arguments(study),
        every=study.every,
        output=study.output,
        status=study.status,
    )
