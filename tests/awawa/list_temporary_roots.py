import tempfile
from pathlib import Path


def list_temporary_roots() -> list[str]:
    return sorted({tempfile.gettempdir(), str(Path(tempfile.gettempdir()).resolve())})
