from brigade.errors import BrigadeError


def apply_actions(actions: tuple) -> int:
    if actions:
        raise BrigadeError(f"the tick has no executor for the action {type(actions[0]).__name__}")
    return 0
