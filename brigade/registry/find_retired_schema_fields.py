import re

from brigade.system.retired_name import RetiredName

RETIRED_FIELDS = {("POLICY", "VERIFY_ROUNDS"): "REPAIR_ROUNDS"}
SCHEMA_LINE = re.compile(r"^SCHEMA (\w+)")
FIELD_LINE = re.compile(r"^\tFIELD (\w+)")


def find_retired_schema_fields(schema: str) -> list[RetiredName]:
    retired = []
    entity_type = None
    for line in schema.splitlines():
        schema_line = SCHEMA_LINE.match(line)
        if schema_line:
            entity_type = schema_line.group(1)
        field_line = FIELD_LINE.match(line)
        new_field = field_line and RETIRED_FIELDS.get((entity_type, field_line.group(1)))
        if new_field:
            retired.append(RetiredName(old=f"{entity_type}.{field_line.group(1)}", new=f"{entity_type}.{new_field}"))
    return retired
