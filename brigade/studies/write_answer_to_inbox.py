from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.write_text_atomically import write_text_atomically

INBOX_DIRECTORY = "inbox"


def write_answer_to_inbox(context: StudyRunContext, publication: AnswerPublication) -> dict:
    path = context.runtime.paths.state_root / INBOX_DIRECTORY / f"{context.run_id}.md"
    write_text_atomically(path, publication.markdown)
    return {"inbox": str(path)}
