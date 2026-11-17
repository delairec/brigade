from collections.abc import Callable
from dataclasses import dataclass

from brigade.tick.apply_actions import AppliedActions
from brigade.tick.build_snapshot import Snapshot


@dataclass(frozen=True)
class Cycles:
    build_snapshot: Callable[[], Snapshot]
    decide: Callable[[Snapshot], tuple]
    apply: Callable[[tuple], AppliedActions]
    cap: int


@dataclass(frozen=True)
class CyclesOutcome:
    actions_applied: int
    actions_failed: int
    merge_commands: tuple[str, ...] = ()


def run_cycles(cycles: Cycles) -> CyclesOutcome:
    actions_applied = 0
    failed = ()
    for _ in range(cycles.cap):
        actions = tuple(action for action in cycles.decide(cycles.build_snapshot()) if action not in failed)
        if not actions:
            break
        applied = cycles.apply(actions)
        actions_applied += applied.applied
        failed += applied.failed
    return CyclesOutcome(actions_applied=actions_applied, actions_failed=len(failed))
