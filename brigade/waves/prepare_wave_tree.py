import argparse
from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entities import read_entities
from brigade.errors import BrigadeError
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.waves.is_milestone_branch_off_the_forge import RecordedMilestoneBranch, is_milestone_branch_off_the_forge
from brigade.waves.locate_forge_branch import locate_forge_branch

TASK_TYPE = "TASK"
MAIN_FIELD = "MAIN"
MILESTONE_PREFIX = "@MILESTONE."


@dataclass(frozen=True)
class WaveTreeReading:
    configuration: Configuration
    read_environment: Callable[[str], dict]


def _locate_branch_ref(runtime: Runtime, reading: WaveTreeReading, project: str, branch: str) -> str:
    entity = find_project(read_projects(runtime), project)
    recorded = RecordedMilestoneBranch(project=entity, branch=branch, read_environment=reading.read_environment)
    if is_milestone_branch_off_the_forge(runtime.run_process, recorded):
        return branch
    return locate_forge_branch(runtime.run_process, entity, branch, reading.read_environment)


def _prepare_tree_at(runtime: Runtime, reading: WaveTreeReading, project: str, branch: str) -> Tree:
    query = argparse.Namespace(
        project=project, ref=_locate_branch_ref(runtime, reading, project, branch), worktree=None
    )
    return prepare_project_tree(query, reading.configuration, runtime)


def _list_milestone_cuts(entries: tuple[LedgerEntry, ...], project: str) -> tuple[MilestoneBranchCut, ...]:
    cuts = {
        entry.event.milestone: entry.event
        for entry in entries
        if isinstance(entry.event, MilestoneBranchCut) and entry.event.project == project
    }
    return tuple(cuts.values())


def _list_open_milestone_cuts(entries: tuple[LedgerEntry, ...], project: str) -> tuple[MilestoneBranchCut, ...]:
    closed = {
        entry.event.milestone
        for entry in entries
        if isinstance(entry.event, MilestoneClosed) and entry.event.project == project
    }
    return tuple(cut for cut in _list_milestone_cuts(entries, project) if cut.milestone not in closed)


def _read_main(runtime: Runtime, project: str) -> str:
    return read_project_field(find_project(read_projects(runtime), project), MAIN_FIELD)


def _holds_the_wave(runtime: Runtime, tree: Tree, cut: MilestoneBranchCut, started: WaveStarted) -> bool:
    of_milestone = read_entities(
        runtime.run_process, tree.root, TASK_TYPE, f"MILESTONE=={MILESTONE_PREFIX}{cut.milestone}"
    )
    return set(started.tasks) <= {task.name for task in of_milestone}


def prepare_wave_tree(runtime: Runtime, reading: WaveTreeReading, started: WaveStarted) -> Tree:
    entries = runtime.read_ledger(runtime.paths.state_root).entries
    for cut in _list_open_milestone_cuts(entries, started.project):
        tree = _prepare_tree_at(runtime, reading, started.project, cut.branch)
        if _holds_the_wave(runtime, tree, cut, started):
            return tree
    return _prepare_tree_at(runtime, reading, started.project, _read_main(runtime, started.project))


def _prepare_cut_tree(runtime: Runtime, reading: WaveTreeReading, cut: MilestoneBranchCut, main: str) -> Tree:
    try:
        return _prepare_tree_at(runtime, reading, cut.project, cut.branch)
    except BrigadeError:
        return _prepare_tree_at(runtime, reading, cut.project, main)


def locate_wave_branch_base(runtime: Runtime, reading: WaveTreeReading, started: WaveStarted) -> str:
    entries = runtime.read_ledger(runtime.paths.state_root).entries
    main = _read_main(runtime, started.project)
    for cut in _list_milestone_cuts(entries, started.project):
        if _holds_the_wave(runtime, _prepare_cut_tree(runtime, reading, cut, main), cut, started):
            return cut.branch
    return main
