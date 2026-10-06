from dataclasses import dataclass

from brigade.commands.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord


@dataclass(frozen=True)
class AwawaPassage:
    project: str
    sha: str
    record: ProcessRecord


def run(request, runtime) -> AwawaPassage:
    tree = prepare_project_tree(request, runtime)
    record = run_awawa(runtime.run_process, tree.root, request.awawa_arguments)
    return AwawaPassage(project=tree.project, sha=tree.sha, record=record)
