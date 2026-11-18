from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, RoleBindings

BINDING_SEPARATOR = "="


def _read_values(project: Entity, field_name: str) -> list[str]:
    return [field.value for field in project.fields if field.name == field_name]


def _read_role_binding(project: Entity, value: str) -> tuple[str, str]:
    slot, separator, name = value.partition(BINDING_SEPARATOR)
    if not separator or not slot.strip() or not name.strip():
        raise BrigadeError(f"@PROJECT.{project.name} has ROLE {value}, not slot=name")
    return slot.strip(), name.strip()


def read_role_bindings(project: Entity | None) -> RoleBindings:
    if project is None:
        return NO_PROJECT_BINDINGS
    path = read_project_field(project, "PATH")
    return RoleBindings(
        project=project.name,
        roles=dict(_read_role_binding(project, value) for value in _read_values(project, "ROLE")),
        roleset=read_project_field(project, "ROLESET"),
        project_path=None if path is None else Path(path),
    )
