import argparse
import dataclasses
import functools
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.commands._resolve_project_forge import resolve_project_forge
from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError, UsageError
from brigade.git.detect_repository import detect_repository
from brigade.git.list_tracked_files import list_tracked_files
from brigade.registry.change_registry import change_registry
from brigade.registry.derive_project_name import derive_project_name
from brigade.registry.discover_project import CORPUS_FILES, ProjectDiscovery, discover_project
from brigade.registry.guess_commands import CommandGuess, guess_commands
from brigade.registry.install_project_corpus import CorpusInstallation, install_project_corpus
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.registry.remove_project_entity import remove_project_entity
from brigade.registry.render_project_entity import render_project_entity
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
INITIAL_STATUS = "active"
NEVER_GUESSED = ()
FIELD_NAME_WIDTH = 12
GUESSED_MARK = "  (guessed)"
NO_CONFIGURATION = "no supported configuration was found"
DEFAULT_CORPUS_FOLDER = "corpus"
PARENT_DIRECTORY = ".."
NOTHING_INSTALLED = None


@dataclass(frozen=True)
class _DocumentField:
    name: str
    value: str
    guessed: bool


class _Registration:
    def __init__(self, runtime: Runtime, entity: Entity, *, force: bool):
        self.runtime = runtime
        self.entity = entity
        self.force = force
        self.replaced = False

    def find_registered(self) -> str | None:
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
        registered_name = self.find_registered()
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


def _choose_corpus_folder(request) -> str:
    folder = posixpath.normpath(request.corpus or DEFAULT_CORPUS_FOLDER)
    if posixpath.isabs(folder) or folder.split(posixpath.sep)[0] == PARENT_DIRECTORY:
        raise UsageError(f"--corpus {request.corpus} is not a folder inside the repository")
    return folder


def _refuse_a_corpus_already_tracked(runtime: Runtime, path: Path) -> None:
    tracked = list_tracked_files(runtime.run_process, path, CORPUS_FILES)
    if tracked:
        raise BrigadeError(f"{path} already tracks {tracked[0]}; --init-corpus would add a second corpus")


def _install_corpus(runtime: Runtime, project: Entity) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    forge_name = read_project_forge(project)
    return install_project_corpus(
        runtime,
        CorpusInstallation(
            project=project,
            forge=resolve_project_forge(project, runtime),
            read_environment=functools.cache(
                lambda key: read_forge_environment(configuration, ForgeSlot(forge_name, key), runtime)
            ),
        ),
    )


def _render_field(field: dict) -> str:
    mark = GUESSED_MARK if field["guessed"] else ""
    return f"{field['name']:<{FIELD_NAME_WIDTH}}{field['value']}{mark}"


def _render_text(document: dict) -> str:
    project = document["project"]
    lines = [
        f"{document['action']} @PROJECT.{project['name']}",
        *(_render_field(field) for field in project["fields"]),
    ]
    if not document["configurations"]:
        lines.append(NO_CONFIGURATION)
    installed = document["installed_corpus"]
    if installed is not NOTHING_INSTALLED:
        lines.append(f"branch {installed['branch']}")
        lines.append(installed["merge_command"] or f"pull request #{installed['pull_request']}")
    return "\n".join(lines)


def project_add(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    path = Path(request.path).resolve()
    name = _choose_name(request, path)
    if not detect_repository(runtime.run_process, path):
        raise BrigadeError(f"{path} is not a git repository")
    if request.corpus is not None and not request.init_corpus:
        raise UsageError("--corpus names the folder of --init-corpus and needs it")
    discovery = discover_project(runtime.run_process, path)
    if request.init_corpus:
        discovery = dataclasses.replace(discovery, corpus=_choose_corpus_folder(request))
        _refuse_a_corpus_already_tracked(runtime, path)
    guess = guess_commands(path)
    fields = _describe_fields(request, discovery, guess)
    project = Entity(name=name, fields=tuple(EntityField(name=field.name, value=field.value) for field in fields))
    registration = _Registration(runtime, project, force=request.force)
    installed = NOTHING_INSTALLED
    if request.init_corpus:
        registration.find_registered()
        installed = _install_corpus(runtime, project)
    change_registry(runtime, f"brigade project add: {name}", registration.rewrite)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "action": "replaced" if registration.replaced else "added",
        "project": {
            "name": name,
            "fields": [{"name": field.name, "value": field.value, "guessed": field.guessed} for field in fields],
        },
        "configurations": list(guess.configurations),
        "installed_corpus": installed,
    }


COMMAND = Command(
    path=("project", "add"),
    help="register a git repository in the operational corpus",
    group_help="register the projects brigade works on, list and show them",
    arguments=(
        Argument(("path",)),
        Argument(("--name",), {"help": "the name of the PROJECT entity; the basename of the path by default"}),
        Argument(("--acceptance",), {"action": "append", "default": [], "help": "a light command run by task check"}),
        Argument(("--heavy",), {"action": "append", "default": [], "help": "a suite left to continuous integration"}),
        Argument(("--setup",), {"action": "append", "default": [], "help": "a per-worktree command"}),
        Argument(("--force",), {"action": "store_true", "help": "replace the project already registered"}),
        Argument(
            ("--init-corpus",),
            {"action": "store_true", "help": "install a corpus on a branch of a repository that tracks no .awawa file"},
        ),
        Argument(("--corpus",), {"help": "the folder --init-corpus installs the corpus in; corpus by default"}),
    ),
    run=project_add,
    render_text=_render_text,
)
