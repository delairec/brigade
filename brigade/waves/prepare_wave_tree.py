import argparse

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.ledger.wave_started import WaveStarted
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration


def prepare_wave_tree(runtime: Runtime, configuration: Configuration, started: WaveStarted) -> Tree:
    query = argparse.Namespace(project=started.project, ref=started.branch, worktree=None)
    return prepare_project_tree(query, configuration, runtime)
