from datetime import datetime

from brigade.errors import BrigadeError
from brigade.studies.read_schedule import read_schedule
from brigade.tick.study_facts import StudyFacts

ACTIVE_STATUS = "active"


def is_study_due(study: StudyFacts, now: datetime) -> bool:
    if study.status != ACTIVE_STATUS or study.every is None:
        return False
    if study.parked:
        return study.quota_resume_at is not None and study.quota_resume_at <= now
    try:
        schedule = read_schedule(study.every)
    except BrigadeError as refusal:
        raise BrigadeError(f"@STUDY.{study.name}: {refusal}") from None
    return study.last_started is None or schedule.has_passed_since(study.last_started, now)
