import argparse

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entities import read_entities
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration

TASK_TYPE = "TASK"
MAIN_FIELD = "MAIN"
MILESTONE_PREFIX = "@MILESTONE."


def _prepare_tree_at(runtime: Runtime, configuration: Configuration, project: str, ref: str) -> Tree:
    query = argparse.Namespace(project=project, ref=ref, worktree=None)
    return prepare_project_tree(query, configuration, runtime)


def _list_open_milestone_cuts(entries: tuple[LedgerEntry, ...], project: str) -> tuple[MilestoneBranchCut, ...]:
    closed = {
        entry.event.milestone
        for entry in entries
        if isinstance(entry.event, MilestoneClosed) and entry.event.project == project
    }
    cuts = {
        entry.event.milestone: entry.event
        for entry in entries
        if isinstance(entry.event, MilestoneBranchCut) and entry.event.project == project
    }
    return tuple(cut for milestone, cut in cuts.items() if milestone not in closed)


def _holds_the_wave(runtime: Runtime, tree: Tree, cut: MilestoneBranchCut, started: WaveStarted) -> bool:
    of_milestone = read_entities(
        runtime.run_process, tree.root, TASK_TYPE, f"MILESTONE=={MILESTONE_PREFIX}{cut.milestone}"
    )
    return set(started.tasks) <= {task.name for task in of_milestone}


def prepare_wave_tree(runtime: Runtime, configuration: Configuration, started: WaveStarted) -> Tree:
    entries = runtime.read_ledger(runtime.paths.state_root).entries
    for cut in _list_open_milestone_cuts(entries, started.project):
        tree = _prepare_tree_at(runtime, configuration, started.project, cut.branch)
        if _holds_the_wave(runtime, tree, cut, started):
            return tree
    main = read_project_field(find_project(read_projects(runtime), started.project), MAIN_FIELD)
    return _prepare_tree_at(runtime, configuration, started.project, main)
