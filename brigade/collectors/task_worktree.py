from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.recipes.locate_recipes import locate_recipes
from brigade.recipes.read_project_commands import read_project_commands
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "task-worktree"
FRESH_AT_EACH_CALL = False
NO_ITEMS = []
ACCEPTANCE_RECIPE = "acceptance"


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    worktree = Path(inputs.parameters["worktree"])
    places = locate_recipes(worktree, project, runtime.paths)
    summary = {
        "checkout": str(worktree),
        "head_tree": str(worktree / read_corpus_workspace(project)),
        "acceptance": [list(argv) for argv in read_project_commands(places, ACCEPTANCE_RECIPE, runtime.run_process)],
    }
    return {**describe_collection(NAME, runtime, summary, NO_ITEMS), "cache": FRESH_AT_EACH_CALL}
