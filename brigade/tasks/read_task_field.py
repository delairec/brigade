from brigade.corpus.read_entities import Entity


def read_task_field(task: Entity, field_name: str) -> tuple[str, ...]:
    return tuple(field.value for field in task.fields if field.name == field_name)
