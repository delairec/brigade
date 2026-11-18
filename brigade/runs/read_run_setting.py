import dataclasses
from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration

CLIENT_FIELD = "CLIENT"


@dataclass(frozen=True)
class RunSettingQuery:
    project: str | None
    slot: str
    on_fallback: bool = False


@dataclass(frozen=True)
class RunSetting:
    configuration: Configuration
    project: Entity | None
    client: str


def _read_project(name: str | None, runtime: Runtime) -> Entity | None:
    if name is None:
        return None
    require_operational_corpus(runtime.paths)
    return find_project(read_projects(runtime), name)


def read_run_setting(query: RunSettingQuery, configuration: Configuration, runtime: Runtime) -> RunSetting:
    project = _read_project(query.project, runtime)
    if query.on_fallback:
        fallback = configuration.fallback
        return RunSetting(
            configuration=dataclasses.replace(configuration, reasoning=fallback.reasoning),
            project=project,
            client=fallback.client,
        )
    client = (
        configuration.slot_clients.get(query.slot) or read_project_field(project, CLIENT_FIELD) or configuration.client
    )
    if client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {runtime.paths.configuration_file}")
    return RunSetting(configuration=configuration, project=project, client=client)
