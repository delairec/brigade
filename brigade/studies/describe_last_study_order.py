from brigade.studies.read_last_study_orders import LastStudyOrder


def describe_last_study_order(last_order: LastStudyOrder | None) -> dict:
    if last_order is None:
        return {"last_run": None, "outcome": None}
    return {"last_run": last_order.run, "outcome": last_order.outcome}
