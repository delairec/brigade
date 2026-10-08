from brigade.corpus.read_entities import Entity


def read_project_field(project: Entity | None, field_name: str) -> str | None:
    if project is None:
        return None
    return next((field.value for field in project.fields if field.name == field_name), None)
