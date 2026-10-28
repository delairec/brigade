import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.git.list_conflicting_files import list_conflicting_files
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.push_branch import REMOTE
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.tick.name_task_branch import name_task_branch
from brigade.verify.find_opened_task import find_opened_task
from brigade.waves.locate_forge_branch import locate_forge_branch

DOCUMENT_SCHEMA_VERSION = 1
ENVIRONMENT_OF_THE_RUN = {}
TASK_NAMED_BY_THE_BRANCH = None


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


def rebase_context(request: argparse.Namespace, runtime: Runtime) -> dict:
    if request.pr is None:
        return _read_unopened_task(runtime)
    worktree = locate_worktree_root(runtime.run_process, Path.cwd())
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
    help="print in one read the branch of a task, its base and the files in conflict",
    group_help="put the pull request of a task back on its base",
    arguments=(
        Argument(
            ("pr",),
            {"type": int, "nargs": "?", "help": "the number of the pull request, none for a task without one"},
        ),
    ),
    run=rebase_context,
    render_text=_render_text,
)
