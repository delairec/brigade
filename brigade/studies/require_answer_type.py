from collections.abc import Callable
from pathlib import Path

from brigade.errors import BrigadeError


def require_answer_type(check_type_declared: Callable[[Path, str], bool], root: Path, answer_type: str) -> None:
    if not check_type_declared(root, answer_type):
        raise BrigadeError(f"the schema of the operational corpus declares no {answer_type}")
