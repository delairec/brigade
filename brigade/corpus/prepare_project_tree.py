import argparse
import dataclasses

from brigade.corpus.prepare_project_checkout import prepare_project_checkout
from brigade.corpus.prepare_tree import Tree
from brigade.errors import ToolFailure
from brigade.registry.find_project import find_project
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration


def prepare_project_tree(request: argparse.Namespace, configuration: Configuration, runtime: Runtime) -> Tree:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), request.project)
    folder = read_corpus_workspace(project)
    tree = prepare_project_checkout(project, request, configuration, runtime)
    workspace = tree.root / folder
    if workspace != tree.root and not workspace.is_dir():
        raise ToolFailure(
            f"the area {folder} of @PROJECT.{project.name} is absent at {tree.sha}: its branch is not merged"
        )
    return dataclasses.replace(tree, root=workspace)
