from brigade.studies.convert_study import Study
from brigade.studies.describe_last_study_order import describe_last_study_order
from brigade.studies.read_last_study_orders import LastStudyOrder


def describe_study_row(study: Study, last_order: LastStudyOrder | None) -> dict:
    return {"name": study.name, "status": study.status, "every": study.every, **describe_last_study_order(last_order)}
