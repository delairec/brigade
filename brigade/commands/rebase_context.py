import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError
from brigade.git.list_conflicting_files import list_conflicting_files
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.push_branch import REMOTE
from brigade.git.read_current_branch import read_current_branch
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.tasks.locate_task_worktree import TASK_BRANCH, locate_task_worktree
from brigade.tick.name_task_branch import name_task_branch
from brigade.verify.find_opened_task import find_opened_task
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.read_wave_milestone import read_wave_milestone

DOCUMENT_SCHEMA_VERSION = 1
ENVIRONMENT_OF_THE_RUN = {}
TASK_NAMED_BY_THE_BRANCH = None
TASK_TYPE = "TASK"
MAIN_FIELD = "MAIN"


def _render_text(document: dict) -> str:
    conflicts = "\n".join(document["conflicts"])
    return f"# branch\n{document['branch']}\n\n# base\n{document['base']}\n\n# conflicts\n{conflicts}"


def _read_unopened_task(runtime: Runtime) -> dict:
    found = locate_task_worktree(runtime, Path.cwd(), TASK_NAMED_BY_THE_BRANCH)
    upstream = locate_forge_branch(
        runtime.run_process, found.project, found.wave_branch, lambda key: ENVIRONMENT_OF_THE_RUN
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": found.project.name,
        "pr": None,
        "task": found.task,
        "branch": name_task_branch(found.wave_branch, found.task),
        "base": found.wave_branch,
        "conflicts": list_conflicting_files(runtime.run_process, found.path, upstream),
    }


def _find_base_of_the_branch(runtime: Runtime, worktree: Path, project, branch: str) -> str:
    entries = read_ledger(runtime.paths.state_root).entries
    if any(
        isinstance(entry.event, MilestoneBranchCut)
        and entry.event.project == project.name
        and entry.event.branch == branch
        for entry in entries
    ):
        return read_project_field(project, MAIN_FIELD)
    started = next(
        (
            entry.event
            for entry in reversed(entries)
            if isinstance(entry.event, WaveStarted)
            and entry.event.project == project.name
            and entry.event.branch == branch
        ),
        None,
    )
    if started is None:
        raise BrigadeError(
            f"the branch {branch} is not a task, a wave or a milestone branch of @PROJECT.{project.name}"
        )
    tasks = (read_entity(runtime.run_process, worktree, TASK_TYPE, task) for task in started.tasks)
    return find_milestone_branch(entries, project.name, read_wave_milestone(started.wave, tasks))


def _read_unopened_branch(runtime: Runtime, worktree: Path, branch: str) -> dict:
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, worktree))
    base = _find_base_of_the_branch(runtime, worktree, project, branch)
    upstream = locate_forge_branch(runtime.run_process, project, base, lambda key: ENVIRONMENT_OF_THE_RUN)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": project.name,
        "pr": None,
        "task": None,
        "branch": branch,
        "base": base,
        "conflicts": list_conflicting_files(runtime.run_process, worktree, upstream),
    }


def rebase_context(request: argparse.Namespace, runtime: Runtime) -> dict:
    worktree = locate_worktree_root(runtime.run_process, Path.cwd())
    if request.pr is None:
        branch = read_current_branch(runtime.run_process, worktree)
        if TASK_BRANCH.fullmatch(branch) is None:
            return _read_unopened_branch(runtime, worktree, branch)
        return _read_unopened_task(runtime)
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, worktree))
    found = find_opened_task(runtime, project.name, request.pr)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": project.name,
        "pr": request.pr,
        "task": found.opened.task,
        "branch": found.opened.branch,
        "base": found.wave_branch,
        "conflicts": list_conflicting_files(runtime.run_process, worktree, f"{REMOTE}/{found.wave_branch}"),
    }


COMMAND = Command(
    path=("rebase", "context"),
    help="print in one read the branch of a task, a wave or a milestone, its base and the files in conflict",
    group_help="put the pull request of a task back on its base",
    arguments=(
        Argument(
            ("pr",),
            {"type": int, "nargs": "?", "help": "the number of the pull request, none for a branch without one"},
        ),
    ),
    run=rebase_context,
    render_text=_render_text,
)
