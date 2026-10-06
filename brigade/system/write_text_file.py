from pathlib import Path

from brigade.errors import CannotWrite


def write_text_file(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
