from brigade.errors import BrigadeError

EXECUTORS = {}


def apply_actions(actions: tuple, runtime) -> int:
    for action in actions:
        executor = EXECUTORS.get(type(action))
        if executor is None:
            raise BrigadeError(f"the tick has no executor for the action {type(action).__name__}")
        executor(action, runtime)
    return len(actions)
