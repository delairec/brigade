from pathlib import Path


def read_input(file: Path) -> str | None:
    try:
        return file.read_text(errors="surrogateescape")
    except PermissionError:
        return None
