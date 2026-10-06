from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.corpus.read_entity_package import read_entity_package
from brigade.errors import BrigadeError
from brigade.roles.check_front_matter import check_front_matter
from brigade.roles.list_built_in_role_files import list_built_in_role_files
from brigade.roles.list_machine_role_files import list_machine_role_files
from brigade.roles.parse_role_file import RoleFile, RoleFileUnreadable, parse_role_file
from brigade.system.read_configuration import Configuration
from brigade.system.read_optional_configuration import read_optional_configuration

CONFIGURATION_FILE = "config.toml"
AGENT_TYPE = "AGENT"
LISTED_VALUE_SEPARATOR = "; "
CAPABILITY_SEPARATOR = ", "
AGENT_FIELDS = (
    ("work", "WORK", LISTED_VALUE_SEPARATOR),
    ("reasoning", "REASONING", LISTED_VALUE_SEPARATOR),
    ("capabilities", "CAPABILITY", CAPABILITY_SEPARATOR),
    ("budget", "BUDGET", LISTED_VALUE_SEPARATOR),
    ("returns", "RETURNS", LISTED_VALUE_SEPARATOR),
)


@dataclass(frozen=True)
class ResolvedRole:
    slot: str
    role: str
    source: str
    front_matter: dict
    body: str


def _read_machine_role_file(path: Path) -> RoleFile:
    try:
        role_file = parse_role_file(path.read_text(encoding="utf-8"))
    except RoleFileUnreadable as unreadable:
        raise BrigadeError(f"{path}: {unreadable}") from None
    problems = check_front_matter(role_file.front_matter)
    if problems:
        raise BrigadeError(f"{path}: {problems[0].key} {problems[0].problem}")
    return role_file


def _find_machine_role(slot: str, config_root: Path):
    role_files = [(path, _read_machine_role_file(path)) for path in list_machine_role_files(config_root)]
    declaring = [(path, role_file) for path, role_file in role_files if role_file.front_matter["slot"] == slot]
    if len(declaring) > 1:
        raise BrigadeError(f"slot {slot} is declared by both {declaring[0][0]} and {declaring[1][0]}")
    if not declaring:
        return None
    return declaring[0][1]


def _join_values(entity: Entity, field_name: str, separator: str) -> str:
    return separator.join(field.value for field in entity.fields if field.name == field_name)


def _describe_agent(entity: Entity, slot: str) -> dict:
    present = {field.name for field in entity.fields}
    declared = {
        key: _join_values(entity, field_name, separator)
        for key, field_name, separator in AGENT_FIELDS
        if field_name in present
    }
    return {"name": entity.name, "slot": slot, **declared}


def _read_agent_role(slot: str, configuration: Configuration, configuration_path: Path, runtime) -> RoleFile:
    name = configuration.slots[slot]
    if configuration.instructions is None:
        raise BrigadeError(f"slots.{slot} binds {name} but no instructions corpus is set in {configuration_path}")
    root = Path(configuration.instructions)
    front_matter = _describe_agent(read_entity(runtime.run_process, root, AGENT_TYPE, name), slot)
    problems = check_front_matter(front_matter)
    if problems:
        raise BrigadeError(f"@{AGENT_TYPE}.{name}: {problems[0].key} {problems[0].problem}")
    body = read_entity_package(runtime.run_process, root, f"@{AGENT_TYPE}.{name}")
    return RoleFile(front_matter=front_matter, body=body)


def _find_built_in_role(slot: str) -> RoleFile:
    role_files = (parse_role_file(entry.read_text(encoding="utf-8")) for entry in list_built_in_role_files())
    return next(role_file for role_file in role_files if role_file.front_matter["slot"] == slot)


def _resolve(slot: str, source: str, role_file: RoleFile) -> ResolvedRole:
    return ResolvedRole(
        slot=slot,
        role=role_file.front_matter["name"],
        source=source,
        front_matter=role_file.front_matter,
        body=role_file.body,
    )


def resolve_role(slot: str, runtime) -> ResolvedRole:
    machine_role = _find_machine_role(slot, runtime.paths.config_root)
    if machine_role is not None:
        return _resolve(slot, "machine", machine_role)
    configuration_path = runtime.paths.config_root / CONFIGURATION_FILE
    configuration = read_optional_configuration(configuration_path)
    if slot in configuration.slots:
        return _resolve(slot, "instructions", _read_agent_role(slot, configuration, configuration_path, runtime))
    return _resolve(slot, "built-in", _find_built_in_role(slot))
