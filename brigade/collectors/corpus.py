import json
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration

NAME = "corpus"
REF_PARAMETER = "ref"
HEAD = "HEAD"
STATUS_ARGUMENTS = ("status", "--json", ".")


@dataclass(frozen=True)
class _TreeSelection:
    project: str
    ref: str
    worktree: Path | None


def collect(environment: dict, runtime: Runtime, configuration: Configuration) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    selection = _TreeSelection(project=project.name, ref=inputs.parameters.get(REF_PARAMETER, HEAD), worktree=None)
    tree = prepare_project_tree(selection, configuration, runtime)
    status = json.loads(run_awawa(runtime.run_process, tree.root, STATUS_ARGUMENTS).stdout)
    summary = {entry["type"]: entry["counts"] for entry in status["types"]}
    return describe_collection(NAME, runtime, summary, status["entities"])
