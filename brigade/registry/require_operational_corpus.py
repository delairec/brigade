from pathlib import Path

from brigade.errors import BrigadeError

SCHEMA_FILE = "_schema.awawa"


def require_operational_corpus(config_root: Path) -> None:
    if not (config_root / SCHEMA_FILE).exists():
        raise BrigadeError("the operational corpus is missing; run brigade init first")
