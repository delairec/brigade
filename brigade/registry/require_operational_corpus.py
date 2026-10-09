from brigade.errors import BrigadeError
from brigade.system.paths import Paths


def require_operational_corpus(paths: Paths) -> None:
    if not paths.schema_file.exists():
        raise BrigadeError("the operational corpus is missing; run brigade init first")
