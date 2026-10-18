from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.git.count_changed_lines import count_changed_lines
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "git-diff-stat"
START_PARAMETER = "from"
END_PARAMETER = "to"
MAIN_FIELD = "MAIN"
HEAD = "HEAD"


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    parameters = inputs.parameters
    if START_PARAMETER in parameters:
        start = parameters[START_PARAMETER]
    else:
        start = read_project_field(require_project_at(read_projects(runtime), inputs.project), MAIN_FIELD)
    changes = count_changed_lines(runtime.run_process, inputs.project, start, parameters.get(END_PARAMETER, HEAD))
    items = [
        {"path": change.path, "insertions": change.insertions, "deletions": change.deletions} for change in changes
    ]
    summary = {
        "files": len(changes),
        "insertions": sum(change.insertions for change in changes),
        "deletions": sum(change.deletions for change in changes),
    }
    return describe_collection(NAME, runtime, summary, items)
