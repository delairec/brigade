from collections.abc import Callable
from dataclasses import dataclass

from brigade.tick.build_snapshot import Snapshot


@dataclass(frozen=True)
class Rounds:
    build_snapshot: Callable[[], Snapshot]
    plan: Callable[[Snapshot], tuple]
    apply: Callable[[tuple], int]
    cap: int


@dataclass(frozen=True)
class RoundsOutcome:
    actions_applied: int


def run_rounds(rounds: Rounds) -> RoundsOutcome:
    actions_applied = 0
    for _ in range(rounds.cap):
        actions = rounds.plan(rounds.build_snapshot())
        if not actions:
            return RoundsOutcome(actions_applied=actions_applied)
        actions_applied += rounds.apply(actions)
    return RoundsOutcome(actions_applied=actions_applied)
