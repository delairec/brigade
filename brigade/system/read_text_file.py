from pathlib import Path

from brigade.errors import BrigadeError


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise BrigadeError(f"cannot read {path}: {error.strerror}") from None
