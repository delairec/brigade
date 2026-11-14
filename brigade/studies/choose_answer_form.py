from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.runtime import Runtime
from brigade.studies.check_patterns import check_patterns
from brigade.studies.convert_study import Study
from brigade.studies.fold_pattern_answer import FoldedAnswer, fold_pattern_answer
from brigade.studies.publish_milestone_report import publish_milestone_report
from brigade.studies.publish_task_report import publish_task_report
from brigade.studies.render_answer import name_answer, render_answer
from brigade.studies.render_report_answer import render_report_answer
from brigade.studies.study_run_context import FIELDS_THE_CLI_FILLS, StudyRunContext

REPORT_FIELDS_THE_CLI_FILLS = (
    "MILESTONE",
    "PROJECT",
    "TASK_ROW",
    "STATISTIC",
    "GRAPH",
    "MANUAL_TEST",
    "INSTRUCTIONS_CHANGE",
    "PARKED_QUESTION",
    "PATTERN_TASK",
)
TASK_REPORT_FIELDS_THE_CLI_FILLS = ("TASK", *REPORT_FIELDS_THE_CLI_FILLS[1:])
PATTERN_TYPE = "PATTERN"
NO_ENTITY = ""


@dataclass(frozen=True)
class AnswerForm:
    name: Callable[[Study, str], str]
    render: Callable[[Runtime, Study, str, list[dict]], str]
    fields_the_cli_fills: tuple[str, ...]
    publish: Callable[[StudyRunContext], dict]
    check: Callable[[Runtime, Path, list[dict]], None]
    fold: Callable[[str, str], FoldedAnswer]


def _render_study_answer(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    return render_answer(study, run_id, collected)


def _render_no_entity(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    return NO_ENTITY


def _publish_nothing(context: StudyRunContext) -> dict:
    return {}


def _check_nothing(runtime: Runtime, directory: Path, collected: list[dict]) -> None:
    pass


def _fold_nothing(held: str, answer: str) -> FoldedAnswer:
    return FoldedAnswer(held=held, new=answer)


def _name_report(study: Study, run_id: str) -> str:
    return f"{study.project}_{study.milestone.milestone}"


def _name_task_report(study: Study, run_id: str) -> str:
    return f"{study.project}_{study.task.task}"


STUDY_ANSWER_FORM = AnswerForm(
    name=name_answer,
    render=_render_study_answer,
    fields_the_cli_fills=FIELDS_THE_CLI_FILLS,
    publish=_publish_nothing,
    check=_check_nothing,
    fold=_fold_nothing,
)
REPORT_ANSWER_FORM = AnswerForm(
    name=_name_report,
    render=render_report_answer,
    fields_the_cli_fills=REPORT_FIELDS_THE_CLI_FILLS,
    publish=publish_milestone_report,
    check=_check_nothing,
    fold=_fold_nothing,
)
TASK_REPORT_ANSWER_FORM = AnswerForm(
    name=_name_task_report,
    render=render_report_answer,
    fields_the_cli_fills=TASK_REPORT_FIELDS_THE_CLI_FILLS,
    publish=publish_task_report,
    check=_check_nothing,
    fold=_fold_nothing,
)
PATTERN_ANSWER_FORM = AnswerForm(
    name=name_answer,
    render=_render_no_entity,
    fields_the_cli_fills=(),
    publish=_publish_nothing,
    check=check_patterns,
    fold=fold_pattern_answer,
)


def choose_answer_form(study: Study) -> AnswerForm:
    if study.milestone is not None:
        return REPORT_ANSWER_FORM
    if study.task is not None:
        return TASK_REPORT_ANSWER_FORM
    if study.answer_type == PATTERN_TYPE:
        return PATTERN_ANSWER_FORM
    return STUDY_ANSWER_FORM
