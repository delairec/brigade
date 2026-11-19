from brigade.ledger.current_digests import CurrentDigests
from brigade.ledger.run_finished import RunFinished


def _choose_current(segments: tuple[RunFinished, ...], current: CurrentDigests) -> CurrentDigests:
    latest_role = next((segment.role_digest for segment in reversed(segments)), None)
    latest_procedures = {segment.procedure: segment.procedure_digest for segment in segments}
    return CurrentDigests(role=current.role or latest_role, procedures={**latest_procedures, **current.procedures})


def _is_current(segment: RunFinished, current: CurrentDigests) -> bool:
    return (
        segment.role_digest is not None
        and segment.role_digest == current.role
        and segment.procedure_digest == current.procedures.get(segment.procedure)
    )


def select_current_segments(segments: tuple[RunFinished, ...], current: CurrentDigests) -> list[RunFinished]:
    chosen = _choose_current(segments, current)
    return [segment for segment in segments if _is_current(segment, chosen)]
