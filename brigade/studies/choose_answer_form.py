from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.runtime import Runtime
from brigade.studies.check_patterns import check_patterns
from brigade.studies.convert_study import Study
from brigade.studies.publish_wave_report import publish_wave_report
from brigade.studies.render_answer import name_answer, render_answer
from brigade.studies.render_report_answer import render_report_answer
from brigade.studies.study_run_context import FIELDS_THE_CLI_FILLS, StudyRunContext

REPORT_FIELDS_THE_CLI_FILLS = (
    "WAVE",
    "PROJECT",
    "TASK_ROW",
    "STATISTIC",
    "GRAPH",
    "MANUAL_TEST",
    "INSTRUCTIONS_CHANGE",
    "PARKED_QUESTION",
    "PATTERN_TASK",
)
PATTERN_TYPE = "PATTERN"
NO_ENTITY = ""


@dataclass(frozen=True)
class AnswerForm:
    name: Callable[[Study, str], str]
    render: Callable[[Runtime, Study, str, list[dict]], str]
    fields_the_cli_fills: tuple[str, ...]
    publish: Callable[[StudyRunContext], dict]
    check: Callable[[Runtime, Path, list[dict]], None]


def _render_study_answer(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    return render_answer(study, run_id, collected)


def _render_no_entity(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    return NO_ENTITY


def _publish_nothing(context: StudyRunContext) -> dict:
    return {}


def _check_nothing(runtime: Runtime, directory: Path, collected: list[dict]) -> None:
    pass


def _name_report(study: Study, run_id: str) -> str:
    return study.wave


STUDY_ANSWER_FORM = AnswerForm(
    name=name_answer,
    render=_render_study_answer,
    fields_the_cli_fills=FIELDS_THE_CLI_FILLS,
    publish=_publish_nothing,
    check=_check_nothing,
)
REPORT_ANSWER_FORM = AnswerForm(
    name=_name_report,
    render=render_report_answer,
    fields_the_cli_fills=REPORT_FIELDS_THE_CLI_FILLS,
    publish=publish_wave_report,
    check=_check_nothing,
)
PATTERN_ANSWER_FORM = AnswerForm(
    name=name_answer,
    render=_render_no_entity,
    fields_the_cli_fills=(),
    publish=_publish_nothing,
    check=check_patterns,
)


def choose_answer_form(study: Study) -> AnswerForm:
    if study.wave is not None:
        return REPORT_ANSWER_FORM
    if study.answer_type == PATTERN_TYPE:
        return PATTERN_ANSWER_FORM
    return STUDY_ANSWER_FORM
