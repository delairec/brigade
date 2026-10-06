import re
from pathlib import Path

OUTSIDE_AN_IDENTIFIER = re.compile(r"[^A-Za-z0-9_]")


def derive_project_name(path: Path) -> str:
    return OUTSIDE_AN_IDENTIFIER.sub("_", path.name)
