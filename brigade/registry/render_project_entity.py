from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.corpus.read_entities import Entity, EntityField

ENTITY_TYPE = "PROJECT"
BARE_FIELDS = ("STATUS",)


def _render_field(field: EntityField) -> str:
    value = field.value if field.name in BARE_FIELDS else quote_awawa_string(field.value)
    return f"\t{field.name} {value}\n"


def render_project_entity(entity: Entity) -> str:
    return f"{ENTITY_TYPE} {entity.name}\n" + "".join(_render_field(field) for field in entity.fields)
