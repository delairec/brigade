from pathlib import Path

from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.tasks.locate_task_worktree import TaskWorktree


def locate_task_corpus(worktree: TaskWorktree) -> Path:
    return worktree.path / read_corpus_workspace(worktree.project)
