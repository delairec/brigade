from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.collecting.read_stale_branches import read_stale_branches
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "stale-branches"
FRESH_AT_EACH_CALL = False


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    items = [{**stale, "fingerprint": stale["branch"]} for stale in read_stale_branches(project, equipment, runtime)]
    return {**describe_collection(NAME, runtime, {"branches": len(items)}, items), "cache": FRESH_AT_EACH_CALL}
