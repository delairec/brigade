import argparse

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime

NAME = "corpus-fmt"
FORMAT_CHECK_ARGUMENTS = ("fmt", "--check", ".")
REFORMAT_PREFIX = "would reformat "
WORKSPACE_PREFIX = "./"
FRESH_AT_EACH_CALL = False


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    selection = argparse.Namespace(project=project.name, ref=read_project_field(project, "MAIN"), worktree=None)
    tree = prepare_project_tree(selection, equipment.configuration, runtime)
    record = run_awawa(runtime.run_process, tree.root, FORMAT_CHECK_ARGUMENTS)
    files = [
        line.removeprefix(REFORMAT_PREFIX).removeprefix(WORKSPACE_PREFIX)
        for line in record.stderr.splitlines()
        if line.startswith(REFORMAT_PREFIX)
    ]
    items = [{"file": file, "fingerprint": file} for file in files]
    return {**describe_collection(NAME, runtime, {"files": len(items)}, items), "cache": FRESH_AT_EACH_CALL}
