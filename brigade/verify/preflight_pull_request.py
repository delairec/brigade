import functools
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.corpus.read_entities import Entity
from brigade.git.count_changed_lines import ChangedFile
from brigade.preflights.read_preflight_file import read_preflight_file
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS, PreflightPlugins, PreflightRun, run_preflight
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.verify.measure_size import measure_size

DOCUMENT_SCHEMA_VERSION = 1
REMOTE_BRANCH_PREFIX = "refs/remotes/origin/"
VERIFY_PULL_REQUEST = "verify-pull-request"
PULL_REQUEST_COLLECTOR = "pull-request"


@dataclass(frozen=True)
class PreflightDemand:
    project: Entity
    task: str
    base_branch: str
    pr: int
    equipment: CollectorEquipment
    plugins: PreflightPlugins


def preflight_pull_request(runtime: Runtime, demand: PreflightDemand) -> dict:
    run = PreflightRun(
        name=VERIFY_PULL_REQUEST,
        project=Path(read_project_field(demand.project, "PATH")),
        parameters={"pr": str(demand.pr), "task": demand.task, "base": demand.base_branch},
        equipment=demand.equipment,
        preflights=(functools.partial(read_preflight_file, BUILT_IN_PREFLIGHTS),),
        plugins=demand.plugins,
    )
    outcome = run_preflight(run, runtime)
    facts = outcome.collected[PULL_REQUEST_COLLECTOR]["summary"]
    changed = tuple(ChangedFile(**changed) for changed in facts["changed"])
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "preflight": VERIFY_PULL_REQUEST,
        "verdict": outcome.verdict,
        "project": demand.project.name,
        "pr": demand.pr,
        "task": demand.task,
        "head": facts["head"],
        "checks": [*outcome.checks, measure_size(changed)],
    }
