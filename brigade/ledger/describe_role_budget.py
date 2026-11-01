import math
from dataclasses import dataclass
from fractions import Fraction

from brigade.ledger.run_finished import RunFinished

TURN_LIMIT_OUTCOME = "turn_limit"
MEASURED_SEGMENTS_FOR_A_CAP = 5
MEASURED_RESTARTS_FOR_A_CAP = 3
USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


@dataclass(frozen=True)
class CurrentDigests:
    role: str | None
    procedures: dict


@dataclass(frozen=True)
class RoleBudget:
    shipped: int
    computed: int | None
    applied: int
    segments: int
    restarts: int
    growth: float | None
    restart_tokens: float | None


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


def _list_restarts(segments: tuple[RunFinished, ...]) -> list[RunFinished]:
    previous_outcomes = {}
    restarts = []
    for segment in segments:
        if previous_outcomes.get(segment.run) == TURN_LIMIT_OUTCOME:
            restarts.append(segment)
        previous_outcomes[segment.run] = segment.outcome
    return restarts


def _fit_growth(measured: list[RunFinished]) -> float | None:
    lengths = [segment.main_steps for segment in measured]
    tokens_per_step = [
        Fraction(sum(getattr(segment.usage, counter) for counter in USAGE_COUNTERS), segment.main_steps)
        for segment in measured
    ]
    mean_length = Fraction(sum(lengths), len(lengths))
    mean_tokens = sum(tokens_per_step) / len(tokens_per_step)
    spread = sum((length - mean_length) ** 2 for length in lengths)
    if spread == 0:
        return None
    covariance = sum(
        (length - mean_length) * (tokens - mean_tokens) for length, tokens in zip(lengths, tokens_per_step, strict=True)
    )
    return float(2 * covariance / spread)


def _compute_cap(growth: float | None, restart_tokens: float | None) -> int | None:
    if restart_tokens is None or growth is None or growth <= 0:
        return None
    return round(math.sqrt(2 * restart_tokens / growth))


def _apply_cap(computed: int | None, shipped: int, segments: int, restarts: int) -> int:
    if computed is None or segments < MEASURED_SEGMENTS_FOR_A_CAP or restarts < MEASURED_RESTARTS_FOR_A_CAP:
        return shipped
    return min(max(computed, math.ceil(shipped / 2)), 2 * shipped)


def describe_role_budget(segments: tuple[RunFinished, ...], shipped: int, current: CurrentDigests) -> RoleBudget:
    chosen = _choose_current(segments, current)
    restarted = {id(segment) for segment in _list_restarts(segments)}
    kept = [segment for segment in segments if _is_current(segment, chosen)]
    measured = [segment for segment in kept if segment.main_steps and segment.usage is not None]
    restarts = [segment for segment in kept if id(segment) in restarted and segment.tokens_to_first_edit is not None]
    growth = _fit_growth(measured) if measured else None
    restart_tokens = sum(segment.tokens_to_first_edit for segment in restarts) / len(restarts) if restarts else None
    computed = _compute_cap(growth, restart_tokens)
    return RoleBudget(
        shipped=shipped,
        computed=computed,
        applied=_apply_cap(computed, shipped, len(measured), len(restarts)),
        segments=len(measured),
        restarts=len(restarts),
        growth=growth,
        restart_tokens=restart_tokens,
    )
