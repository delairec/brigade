from brigade.errors import BrigadeError
from brigade.studies.locate_study_project import locate_study_project
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext


def open_answer_issue(context: StudyRunContext, publication: AnswerPublication) -> dict:
    project = locate_study_project(context)
    if project.forge is None:
        raise BrigadeError(f"the output {context.study.output} needs a project with a forge")
    forge = context.equipment.resolve_forge(project.forge)
    issue = forge.open_issue(
        {"repository": str(project.path), "title": publication.title, "body": publication.markdown}, context.runtime
    )
    return {"issue": issue["url"]}
