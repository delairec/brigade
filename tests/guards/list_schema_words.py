import re

_SCHEMA_HEADER = re.compile(r"^SCHEMA (\S+)$")
_FIELD_LINE = re.compile(r"^(\t+)FIELD (\S+)")
_EVERY_ENTITY = "*"


def list_schema_words(schema: str) -> list[str]:
    words = []
    entity: list[str] = []
    fields: list[str] = []
    for line in schema.splitlines():
        header = _SCHEMA_HEADER.match(line)
        field = _FIELD_LINE.match(line)
        if header:
            entity = [] if header[1] == _EVERY_ENTITY else [header[1]]
            words += entity
        elif field:
            fields = [*fields[: len(field[1]) - 1], field[2]]
            words.append(".".join(entity + fields))
    return words
