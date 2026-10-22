from collections.abc import Callable
from dataclasses import dataclass

from brigade.tick.apply_actions import AppliedActions
from brigade.tick.build_snapshot import Snapshot


@dataclass(frozen=True)
class Rounds:
    build_snapshot: Callable[[], Snapshot]
    plan: Callable[[Snapshot], tuple]
    apply: Callable[[tuple], AppliedActions]
    cap: int


@dataclass(frozen=True)
class RoundsOutcome:
    actions_applied: int
    actions_failed: int


def run_rounds(rounds: Rounds) -> RoundsOutcome:
    actions_applied = 0
    failed = ()
    for _ in range(rounds.cap):
        actions = tuple(action for action in rounds.plan(rounds.build_snapshot()) if action not in failed)
        if not actions:
            break
        applied = rounds.apply(actions)
        actions_applied += applied.applied
        failed += applied.failed
    return RoundsOutcome(actions_applied=actions_applied, actions_failed=len(failed))
