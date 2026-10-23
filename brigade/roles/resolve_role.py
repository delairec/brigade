from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.corpus.read_entity_package import read_entity_package
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.roles.check_front_matter import check_front_matter
from brigade.roles.list_built_in_role_files import list_built_in_role_files
from brigade.roles.list_machine_role_files import list_machine_role_files
from brigade.roles.parse_role_file import RoleFile, RoleFileUnreadable, parse_role_file
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration

ROLE_FILE_PATTERN = "*.md"
BUILT_IN_ROLESET = "builtin"
CORPUS_ROLESET = "corpus"
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
class RoleBindings:
    project: str | None
    roles: dict
    roleset: str | None
    project_path: Path | None


NO_PROJECT_BINDINGS = RoleBindings(project=None, roles={}, roleset=None, project_path=None)


@dataclass(frozen=True)
class RoleSource:
    label: str
    find_by_slot: Callable[[str], RoleFile | None]
    find_by_name: Callable[[str], RoleFile | None]


@dataclass(frozen=True)
class AgentLookup:
    configuration: Configuration
    runtime: Runtime


@dataclass(frozen=True)
class ResolvedRole:
    slot: str
    role: str
    source: str
    front_matter: dict
    body: str


def _read_role_file(path: Path) -> RoleFile:
    try:
        role_file = parse_role_file(path.read_text(encoding="utf-8"))
    except RoleFileUnreadable as unreadable:
        raise BrigadeError(f"{path}: {unreadable}") from None
    problems = check_front_matter(role_file.front_matter)
    if problems:
        raise BrigadeError(f"{path}: {problems[0].key} {problems[0].problem}")
    return role_file


def _read_role_files(paths: tuple[Path, ...]) -> list[tuple[Path, RoleFile]]:
    return [(path, _read_role_file(path)) for path in paths]


def _find_declaring(role_files: list[tuple[Path, RoleFile]], slot: str) -> RoleFile | None:
    declaring = [(path, role_file) for path, role_file in role_files if role_file.front_matter["slot"] == slot]
    if len(declaring) > 1:
        raise BrigadeError(f"slot {slot} is declared by both {declaring[0][0]} and {declaring[1][0]}")
    if not declaring:
        return None
    return declaring[0][1]


def _find_named(role_files: list[tuple[Path, RoleFile]], name: str) -> RoleFile | None:
    return next((role_file for _, role_file in role_files if role_file.front_matter["name"] == name), None)


def _list_directory_role_files(directory: Path) -> tuple[Path, ...]:
    return tuple(sorted(directory.glob(ROLE_FILE_PATTERN)))


def _create_directory_source(label: str, role_file_paths: tuple[Path, ...]) -> RoleSource:
    role_files = _read_role_files(role_file_paths)
    return RoleSource(
        label=label,
        find_by_slot=lambda slot: _find_declaring(role_files, slot),
        find_by_name=lambda name: _find_named(role_files, name),
    )


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


def _read_agent(name: str, slot: str, root: Path, runtime: Runtime) -> RoleFile:
    front_matter = _describe_agent(read_entity(runtime.run_process, root, AGENT_TYPE, name), slot)
    problems = check_front_matter(front_matter)
    if problems:
        raise BrigadeError(f"@{AGENT_TYPE}.{name}: {problems[0].key} {problems[0].problem}")
    body = read_entity_package(runtime.run_process, root, f"@{AGENT_TYPE}.{name}")
    return RoleFile(front_matter=front_matter, body=body)


def _find_bound_agent(lookup: AgentLookup, slot: str) -> RoleFile | None:
    configuration = lookup.configuration
    if slot not in configuration.slots:
        return None
    name = configuration.slots[slot]
    if configuration.instructions is None:
        raise BrigadeError(
            f"slots.{slot} binds {name} but no instructions corpus is set in {lookup.runtime.paths.configuration_file}"
        )
    return _read_agent(name, slot, Path(configuration.instructions), lookup.runtime)


def _find_named_agent(lookup: AgentLookup, slot: str, name: str) -> RoleFile | None:
    configuration = lookup.configuration
    if configuration.instructions is None:
        return None
    try:
        return _read_agent(name, slot, Path(configuration.instructions), lookup.runtime)
    except EntityNotDefined:
        return None


def _create_agent_source(lookup: AgentLookup, slot: str) -> RoleSource:
    return RoleSource(
        label="instructions",
        find_by_slot=lambda bound_slot: _find_bound_agent(lookup, bound_slot),
        find_by_name=lambda name: _find_named_agent(lookup, slot, name),
    )


def _create_built_in_source() -> RoleSource:
    role_files = [
        (Path(entry.name), parse_role_file(entry.read_text(encoding="utf-8"))) for entry in list_built_in_role_files()
    ]
    return RoleSource(
        label="built-in",
        find_by_slot=lambda slot: _find_declaring(role_files, slot),
        find_by_name=lambda name: _find_named(role_files, name),
    )


def _locate_roleset(bindings: RoleBindings) -> Path:
    directory = Path(bindings.roleset)
    if directory.is_absolute() or bindings.project_path is None:
        return directory
    return bindings.project_path / directory


def _list_sources(slot: str, bindings: RoleBindings, lookup: AgentLookup) -> list[RoleSource]:
    if bindings.roleset == BUILT_IN_ROLESET:
        return [_create_built_in_source()]
    if bindings.roleset is not None and bindings.roleset != CORPUS_ROLESET:
        roleset_files = _list_directory_role_files(_locate_roleset(bindings))
        return [_create_directory_source("roleset", roleset_files), _create_built_in_source()]
    machine_sources = []
    if bindings.roleset is None:
        machine_sources = [
            _create_directory_source("machine", list_machine_role_files(lookup.runtime.paths.config_root))
        ]
    return [*machine_sources, _create_agent_source(lookup, slot), _create_built_in_source()]


def _resolve(slot: str, source: str, role_file: RoleFile) -> ResolvedRole:
    return ResolvedRole(
        slot=slot,
        role=role_file.front_matter["name"],
        source=source,
        front_matter=role_file.front_matter,
        body=role_file.body,
    )


def _resolve_bound_name(slot: str, bindings: RoleBindings, sources: list[RoleSource]) -> ResolvedRole:
    name = bindings.roles[slot]
    for source in sources:
        role_file = source.find_by_name(name)
        if role_file is not None:
            return _resolve(slot, source.label, role_file)
    raise BrigadeError(f"@PROJECT.{bindings.project} binds {slot} to {name}, a role found nowhere")


def resolve_role(slot: str, runtime: Runtime, bindings: RoleBindings, configuration: Configuration) -> ResolvedRole:
    sources = _list_sources(slot, bindings, AgentLookup(configuration=configuration, runtime=runtime))
    if slot in bindings.roles:
        return _resolve_bound_name(slot, bindings, sources)
    for source in sources:
        role_file = source.find_by_slot(slot)
        if role_file is not None:
            return _resolve(slot, source.label, role_file)
    raise BrigadeError(f"no role declares the slot {slot}")
