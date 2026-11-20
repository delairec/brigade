import argparse
import dataclasses

from brigade.corpus.prepare_project_checkout import prepare_project_checkout
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entities import Entity
from brigade.errors import ToolFailure
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration


def prepare_registered_tree(
    project: Entity, request: argparse.Namespace, configuration: Configuration, runtime: Runtime
) -> Tree:
    folder = read_corpus_workspace(project)
    tree = prepare_project_checkout(project, request, configuration, runtime)
    workspace = tree.root / folder
    if workspace != tree.root and not workspace.is_dir():
        raise ToolFailure(
            f"the area {folder} of @PROJECT.{project.name} is absent at {tree.sha}: its branch is not merged"
        )
    return dataclasses.replace(tree, root=workspace)
