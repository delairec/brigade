from dataclasses import dataclass

from brigade.studies.study_run_context import ANSWER_FILE, StudyRunContext


@dataclass(frozen=True)
class AnswerPublication:
    title: str
    markdown: str


def _render_markdown(entity: dict) -> str:
    fields = "".join(f"- {field['name']}: {field['value']}\n" for field in entity["fields"])
    return f"# {entity['type']} {entity['name']}\n\n{fields}"


def present_answer(context: StudyRunContext) -> AnswerPublication:
    rendering = context.equipment.document.render_document(
        {"path": str(context.run_directory / ANSWER_FILE)}, context.runtime
    )
    return AnswerPublication(
        title=f"Study {context.study.name}, run {context.run_id}",
        markdown="\n".join(_render_markdown(entity) for entity in rendering["entities"]),
    )
