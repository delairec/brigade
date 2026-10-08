from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration, read_configuration

CONFIGURATION_FILE = "config.toml"
CLIENT_FIELD = "CLIENT"


@dataclass(frozen=True)
class RunSetting:
    configuration: Configuration
    project: Entity | None
    client: str


def _read_project(name: str | None, runtime: Runtime) -> Entity | None:
    if name is None:
        return None
    require_operational_corpus(runtime.paths.config_root)
    return find_project(read_projects(runtime), name)


def read_run_setting(project_name: str | None, runtime: Runtime) -> RunSetting:
    configuration_path = runtime.paths.config_root / CONFIGURATION_FILE
    configuration = read_configuration(configuration_path)
    project = _read_project(project_name, runtime)
    client = read_project_field(project, CLIENT_FIELD) or configuration.client
    if client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {configuration_path}")
    return RunSetting(configuration=configuration, project=project, client=client)
