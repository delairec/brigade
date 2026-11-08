import re

from brigade.registry.render_project_schema import STRING_DECLARATION, render_area_schema

SCHEMA_START = re.compile(r"^(?=SCHEMA )", re.MULTILINE)
TYPES_OF_EVERY_AREA = frozenset({"MILESTONE", "TASK", "DECISION", "OPEN_QUESTION"})
TASK_TYPE = "TASK"


def _read_declarations(schema: str) -> dict[str, str]:
    declarations = [text for text in SCHEMA_START.split(schema) if text.startswith("SCHEMA ")]
    return {text.split()[1]: text for text in declarations}


def is_area_schema(schema: str) -> bool:
    declarations = _read_declarations(schema)
    if not TYPES_OF_EVERY_AREA <= declarations.keys() <= _read_declarations(render_area_schema()).keys():
        return False
    return STRING_DECLARATION in declarations[TASK_TYPE]
