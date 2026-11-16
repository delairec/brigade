from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.corpus.read_entities import Entity
from brigade.git.count_changed_lines import ChangedFile
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS, PreflightRun, run_preflight
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import read_project_forge
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.verify.measure_size import measure_size

DOCUMENT_SCHEMA_VERSION = 1
REMOTE_BRANCH_PREFIX = "refs/remotes/origin/"
VERIFY_PULL_REQUEST = "verify-pull-request"
PULL_REQUEST_COLLECTOR = "pull-request"
CLIENT_KIND = "client"


@dataclass(frozen=True)
class PreflightDemand:
    project: Entity
    task: str
    base_branch: str
    pr: int
    forge: object
    environment: dict
    configuration: Configuration


def _equip(runtime: Runtime, demand: PreflightDemand) -> CollectorEquipment:
    return CollectorEquipment(
        configuration=demand.configuration,
        forge=demand.forge,
        forge_name=read_project_forge(demand.project),
        resolve_client=lambda name: runtime.resolve_plugin(CLIENT_KIND, name),
    )


def preflight_pull_request(runtime: Runtime, demand: PreflightDemand) -> dict:
    run = PreflightRun(
        name=VERIFY_PULL_REQUEST,
        project=Path(read_project_field(demand.project, "PATH")),
        parameters={"pr": str(demand.pr), "task": demand.task, "base": demand.base_branch},
        equipment=_equip(runtime, demand),
        preflights=BUILT_IN_PREFLIGHTS,
    )
    outcome = run_preflight(run, runtime)
    facts = outcome.collected[PULL_REQUEST_COLLECTOR]["summary"]
    changed = tuple(ChangedFile(**changed) for changed in facts["changed"])
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": demand.project.name,
        "pr": demand.pr,
        "task": demand.task,
        "head": facts["head"],
        "checks": [*outcome.checks, measure_size(changed)],
    }
