import argparse

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entity import Entity, read_entity
from brigade.registry.find_project import find_project
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree

TASK_TYPE = "TASK"
NO_WORKTREE = None
NO_TASK_RULED = None


def read_ruled_task(
    runtime: Runtime, configuration: Configuration, action: LaunchTask, prepared: PreparedWorktree
) -> Entity | None:
    if prepared.on_start:
        return NO_TASK_RULED
    query = argparse.Namespace(project=action.project, ref=prepared.worktree.start, worktree=NO_WORKTREE)
    tree = prepare_project_tree(query, configuration, runtime)
    on_the_wave_branch = read_entity(runtime.run_process, tree.root, TASK_TYPE, action.task)
    in_the_worktree = read_entity(
        runtime.run_process,
        prepared.worktree.path / read_corpus_workspace(find_project(read_projects(runtime), action.project)),
        TASK_TYPE,
        action.task,
    )
    return NO_TASK_RULED if on_the_wave_branch == in_the_worktree else on_the_wave_branch
