from brigade.corpus.read_entities import Entity
from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA
from brigade.registry.read_corpus_workspace import AREA_MODE, MODE_FIELD
from brigade.registry.read_project_field import read_project_field

ANCHOR_DECLARATION = "FIELD IMPL anchor\n"
STRING_DECLARATION = "FIELD IMPL string\n"


def render_project_schema(project: Entity) -> str:
    schema = SHIPPED_PROJECT_SCHEMA.read_text(encoding="utf-8")
    if read_project_field(project, MODE_FIELD) == AREA_MODE:
        return schema.replace(ANCHOR_DECLARATION, STRING_DECLARATION)
    return schema
