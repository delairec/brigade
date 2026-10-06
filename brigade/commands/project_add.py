import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError, UsageError
from brigade.git.detect_repository import detect_repository
from brigade.registry.change_registry import change_registry
from brigade.registry.derive_project_name import derive_project_name
from brigade.registry.discover_project import ProjectDiscovery, discover_project
from brigade.registry.guess_commands import CommandGuess, guess_commands
from brigade.registry.read_projects import read_projects
from brigade.registry.remove_project_entity import remove_project_entity
from brigade.registry.render_project_entity import render_project_entity
from brigade.registry.require_operational_corpus import require_operational_corpus

DOCUMENT_SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
INITIAL_STATUS = "active"
NEVER_GUESSED = ()


@dataclass(frozen=True)
class _DocumentField:
    name: str
    value: str
    guessed: bool


class _Registration:
    def __init__(self, runtime, entity: Entity, force: bool):
        self.runtime = runtime
        self.entity = entity
        self.force = force
        self.replaced = False

    def _find_registered(self) -> Optional[str]:
        projects = read_projects(self.runtime)
        path = next(field for field in self.entity.fields if field.name == "PATH")
        same_path = [project.name for project in projects if path in project.fields]
        if same_path and not self.force:
            raise BrigadeError(f"{path.value} is already registered as @PROJECT.{same_path[0]}; --force replaces it")
        same_name = [project.name for project in projects if project.name == self.entity.name]
        if same_name and not self.force:
            raise BrigadeError(f"@PROJECT.{self.entity.name} is already registered; --force replaces it")
        return next(iter(same_path + same_name), None)

    def rewrite(self, text: str) -> str:
        registered_name = self._find_registered()
        if registered_name is not None:
            text = remove_project_entity(text, registered_name)
            self.replaced = True
        kept = text.rstrip("\n")
        separator = "\n\n" if kept else ""
        return kept + separator + render_project_entity(self.entity)


def _describe_commands(name: str, given: list[str], guessed: tuple[str, ...]) -> list[_DocumentField]:
    if given:
        return [_DocumentField(name=name, value=value, guessed=False) for value in given]
    return [_DocumentField(name=name, value=value, guessed=True) for value in guessed]


def _describe_fields(request, discovery: ProjectDiscovery, guess: CommandGuess) -> list[_DocumentField]:
    discovered = (
        ("PATH", str(discovery.path)),
        ("REMOTE", discovery.remote),
        ("MAIN", discovery.main),
        ("CORPUS", discovery.corpus),
    )
    return [
        *(_DocumentField(name=name, value=value, guessed=False) for name, value in discovered if value is not None),
        *_describe_commands("ACCEPTANCE", request.acceptance, guess.acceptance),
        *_describe_commands("HEAVY", request.heavy, NEVER_GUESSED),
        *_describe_commands("SETUP", request.setup, guess.setup),
        _DocumentField(name="FORGE", value=discovery.forge, guessed=False),
        _DocumentField(name="STATUS", value=INITIAL_STATUS, guessed=False),
    ]


def _choose_name(request, path: Path) -> str:
    if request.name is None:
        return derive_project_name(path)
    if IDENTIFIER.fullmatch(request.name) is None:
        raise UsageError(f"--name {request.name} is not an identifier: letters, digits and _ only")
    return request.name


def project_add(request, runtime) -> dict:
    require_operational_corpus(runtime.paths.config_root)
    path = Path(request.path).resolve()
    name = _choose_name(request, path)
    if not detect_repository(runtime.run_process, path):
        raise BrigadeError(f"{path} is not a git repository")
    guess = guess_commands(path)
    fields = _describe_fields(request, discover_project(runtime.run_process, path), guess)
    registration = _Registration(
        runtime,
        Entity(name=name, fields=tuple(EntityField(name=field.name, value=field.value) for field in fields)),
        request.force,
    )
    change_registry(runtime, f"brigade project add: {name}", registration.rewrite)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "action": "replaced" if registration.replaced else "added",
        "project": {
            "name": name,
            "fields": [{"name": field.name, "value": field.value, "guessed": field.guessed} for field in fields],
        },
        "configurations": list(guess.configurations),
    }
