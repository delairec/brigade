FINISHED = "finished"


def list_segment_outcomes(state: str, segments: list[dict]) -> list[str]:
    outcomes = [segment["outcome"] for segment in segments if segment["outcome"] is not None]
    return outcomes if state == FINISHED else [*outcomes, state]
