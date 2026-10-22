from collections.abc import Callable, Mapping
from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.ledger.tick_action_failed import TickActionFailed

NAMED_NOWHERE = None


@dataclass(frozen=True)
class AppliedActions:
    applied: int
    failed: tuple


def _describe_failure(action: object, error: BrigadeError) -> TickActionFailed:
    return TickActionFailed(
        action=type(action).__name__,
        project=getattr(action, "project", NAMED_NOWHERE),
        wave=getattr(action, "wave", NAMED_NOWHERE),
        task=getattr(action, "task", NAMED_NOWHERE),
        error=str(error),
    )


def apply_actions(
    actions: tuple,
    executors: Mapping[type, Callable[[object], None]],
    record_failure: Callable[[TickActionFailed], None],
) -> AppliedActions:
    failed = []
    for action in actions:
        execute = executors.get(type(action))
        if execute is None:
            raise BrigadeError(f"the tick has no executor for the action {type(action).__name__}")
        try:
            execute(action)
        except BrigadeError as error:
            record_failure(_describe_failure(action, error))
            failed.append(action)
    return AppliedActions(applied=len(actions) - len(failed), failed=tuple(failed))
