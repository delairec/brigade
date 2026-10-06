from brigade.corpus.read_entities import Entity, EntityField

ENTITY_TYPE = "PROJECT"
BARE_FIELDS = ("STATUS",)


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_field(field: EntityField) -> str:
    value = field.value if field.name in BARE_FIELDS else _quote(field.value)
    return f"\t{field.name} {value}\n"


def render_project_entity(entity: Entity) -> str:
    return f"{ENTITY_TYPE} {entity.name}\n" + "".join(_render_field(field) for field in entity.fields)
