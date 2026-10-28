from dataclasses import dataclass

from brigade.reports.render_report_markdown import render_report_markdown
from brigade.studies.study_run_context import ANSWER_FILE, StudyRunContext


@dataclass(frozen=True)
class AnswerPublication:
    title: str
    markdown: str


def present_answer(context: StudyRunContext) -> AnswerPublication:
    rendering = context.equipment.document.render_document(
        {"path": str(context.run_directory / ANSWER_FILE)}, context.runtime
    )
    return AnswerPublication(
        title=f"Study {context.study.name}, run {context.run_id}",
        markdown="\n".join(render_report_markdown(entity) for entity in rendering["entities"]),
    )
