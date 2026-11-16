from brigade.errors import BrigadeError
from brigade.registry.find_retired_schema_fields import find_retired_schema_fields
from brigade.system.paths import Paths


def require_operational_corpus(paths: Paths) -> None:
    if not paths.schema_file.exists():
        raise BrigadeError("the operational corpus is missing; run brigade init first")
    retired = find_retired_schema_fields(paths.schema_file.read_text())
    if retired:
        names = ", ".join(f"{name.old}, now named {name.new}" for name in retired)
        raise BrigadeError(f"{paths.schema_file} declares {names}; rename it in the schema and in its entities")
