from brigade.ledger.run_finished import RunFinished


def is_measured_segment(segment: RunFinished) -> bool:
    return bool(segment.main_turns) and segment.usage is not None
