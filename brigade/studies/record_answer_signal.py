import hashlib

from brigade.inbox.name_signal import name_signal
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import STUDY_KIND, StudyRunContext

FINGERPRINT_LENGTH = 12


def record_answer_signal(context: StudyRunContext, publication: AnswerPublication) -> dict:
    study = context.study.name
    digest = hashlib.sha256(publication.markdown.encode()).hexdigest()[:FINGERPRINT_LENGTH]
    fingerprint = f"study:{study}:{digest}"
    record_signal(
        context.runtime.paths,
        context.runtime.now,
        NewSignal(
            kind=STUDY_KIND,
            project=context.study.project,
            fingerprint=fingerprint,
            evidence={"study": study, "run": context.run_id, "answer": publication.markdown},
        ),
    )
    return {"signal": name_signal(fingerprint), "fingerprint": fingerprint}
