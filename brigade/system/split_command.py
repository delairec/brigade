import shlex

from brigade.errors import BrigadeError


def split_command(command: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(command))
    except ValueError as error:
        raise BrigadeError(f"the command {command} cannot be split into an argv: {error}") from None
