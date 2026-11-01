import argparse
import json

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "corpus-lint"
LINT_ARGUMENTS = ("lint", "--strict", "--json", ".")
WORKSPACE_PREFIX = "./"
NO_ENTITY = "none"
FRESH_AT_EACH_CALL = False


def _name_entity(entity: dict | None) -> str:
    if entity is None:
        return NO_ENTITY
    return f"{entity['type']}.{entity['name']}"


def _describe_item(diagnostic: dict) -> dict:
    file = diagnostic["file"].removeprefix(WORKSPACE_PREFIX)
    fingerprint = f"{diagnostic['rule']}:{file}:{_name_entity(diagnostic['entity'])}"
    return {**diagnostic, "file": file, "fingerprint": fingerprint}


def _lint_main_branch(project, equipment: CollectorEquipment, runtime: Runtime) -> list[dict]:
    selection = argparse.Namespace(project=project.name, ref=read_project_field(project, "MAIN"), worktree=None)
    tree = prepare_project_tree(selection, equipment.configuration, runtime)
    return json.loads(run_awawa(runtime.run_process, tree.root, LINT_ARGUMENTS).stdout)["diagnostics"]


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    items = []
    if read_project_field(project, "CORPUS") is not None:
        items = [_describe_item(diagnostic) for diagnostic in _lint_main_branch(project, equipment, runtime)]
    return {**describe_collection(NAME, runtime, {"diagnostics": len(items)}, items), "cache": FRESH_AT_EACH_CALL}
