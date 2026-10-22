from collections.abc import Callable
from dataclasses import dataclass

from brigade.runtime import Runtime
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
)


@dataclass(frozen=True)
class AnswerForm:
    name: Callable[[Study, str], str]
    render: Callable[[Runtime, Study, str, list[dict]], str]
    fields_the_cli_fills: tuple[str, ...]
    publish: Callable[[StudyRunContext], dict]


def _render_study_answer(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    return render_answer(study, run_id, collected)


def _publish_nothing(context: StudyRunContext) -> dict:
    return {}


def _name_report(study: Study, run_id: str) -> str:
    return study.wave


STUDY_ANSWER_FORM = AnswerForm(
    name=name_answer,
    render=_render_study_answer,
    fields_the_cli_fills=FIELDS_THE_CLI_FILLS,
    publish=_publish_nothing,
)
REPORT_ANSWER_FORM = AnswerForm(
    name=_name_report,
    render=render_report_answer,
    fields_the_cli_fills=REPORT_FIELDS_THE_CLI_FILLS,
    publish=publish_wave_report,
)


def choose_answer_form(study: Study) -> AnswerForm:
    if study.wave is None:
        return STUDY_ANSWER_FORM
    return REPORT_ANSWER_FORM
