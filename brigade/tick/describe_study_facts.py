from brigade.studies.convert_study import Study
from brigade.studies.read_last_study_orders import LastStudyOrder
from brigade.tick.study_facts import StudyFacts

PARKED_OUTCOME = "parked"


def describe_study_facts(study: Study, last_order: LastStudyOrder | None) -> StudyFacts:
    return StudyFacts(
        name=study.name,
        slot=study.slot,
        every=study.every,
        status=study.status,
        last_started=None if last_order is None else last_order.started,
        parked=last_order is not None and last_order.outcome == PARKED_OUTCOME,
    )
