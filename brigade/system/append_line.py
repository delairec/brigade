from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.create_directory import create_directory

LINE_END = "\n"


def append_line(path: Path, line: str) -> None:
    create_directory(path.parent)
    try:
        with path.open("a", encoding="utf-8") as appended:
            appended.write(line + LINE_END)
            appended.flush()
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
