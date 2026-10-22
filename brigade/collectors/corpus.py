import json
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entity import UNKNOWN_ENTITY_DIAGNOSTIC
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import EntityNotDefined
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "corpus"
REF_PARAMETER = "ref"
HEAD = "HEAD"
STATUS_ARGUMENTS = ("status", "--json", ".")
ENTITIES_PARAMETER = "entities"
ENTITY_SEPARATOR = ","


@dataclass(frozen=True)
class _TreeSelection:
    project: str
    ref: str
    worktree: Path | None


def _show_entity(runtime: Runtime, root: Path, selection: _TreeSelection, target: str) -> dict:
    record = run_awawa(runtime.run_process, root, ("show", target, "--json", "."))
    if UNKNOWN_ENTITY_DIAGNOSTIC in record.stderr:
        raise EntityNotDefined(f"{target} is not defined in the corpus of {selection.project} at {selection.ref}")
    return json.loads(record.stdout)


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    selection = _TreeSelection(project=project.name, ref=inputs.parameters.get(REF_PARAMETER, HEAD), worktree=None)
    tree = prepare_project_tree(selection, equipment.configuration, runtime)
    status = json.loads(run_awawa(runtime.run_process, tree.root, STATUS_ARGUMENTS).stdout)
    summary = {entry["type"]: entry["counts"] for entry in status["types"]}
    if ENTITIES_PARAMETER not in inputs.parameters:
        return describe_collection(NAME, runtime, summary, status["entities"])
    targets = inputs.parameters[ENTITIES_PARAMETER].split(ENTITY_SEPARATOR)
    items = [_show_entity(runtime, tree.root, selection, target) for target in targets]
    return describe_collection(NAME, runtime, summary, items)
