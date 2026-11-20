import argparse

from brigade.corpus.prepare_registered_tree import prepare_registered_tree
from brigade.corpus.prepare_tree import Tree
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration


def prepare_project_tree(request: argparse.Namespace, configuration: Configuration, runtime: Runtime) -> Tree:
    require_operational_corpus(runtime.paths)
    return prepare_registered_tree(
        find_project(read_projects(runtime), request.project), request, configuration, runtime
    )
