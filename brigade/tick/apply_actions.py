from collections.abc import Callable, Mapping

from brigade.errors import BrigadeError


def apply_actions(actions: tuple, executors: Mapping[type, Callable[[object], None]]) -> int:
    for action in actions:
        execute = executors.get(type(action))
        if execute is None:
            raise BrigadeError(f"the tick has no executor for the action {type(action).__name__}")
        execute(action)
    return len(actions)
