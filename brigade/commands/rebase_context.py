from pathlib import Path

from brigade.command import Argument, Command
from brigade.git.list_conflicting_files import list_conflicting_files
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.push_branch import REMOTE
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.verify.find_opened_task import find_opened_task

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    conflicts = "\n".join(document["conflicts"])
    return f"# branch\n{document['branch']}\n\n# base\n{document['base']}\n\n# conflicts\n{conflicts}"


def _decide_exit_code(document: dict) -> int:
    return 0


def rebase_context(request, runtime: Runtime) -> dict:
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
    help="print in one read the branch of the pull request of a task, its base and the files in conflict",
    group_help="put the pull request of a task back on its base",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=rebase_context,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
