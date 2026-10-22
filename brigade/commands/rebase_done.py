from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.git.check_ancestor import check_ancestor
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.push_branch import REMOTE
from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.verify.find_opened_task import find_opened_task

DOCUMENT_SCHEMA_VERSION = 1
ENVIRONMENT_OF_THE_RUN = {}
NOT_AN_ANCESTOR = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return (
        f"{document['branch']} pushed at {document['head']} on top of {document['base']}"
        f" for #{document['pr']}, @TASK.{document['task']}"
    )


def _decide_exit_code(document: dict) -> int:
    return 0


def rebase_done(request, runtime: Runtime) -> dict:
    run_process = runtime.run_process
    worktree = locate_worktree_root(run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(run_process, worktree))
    found = find_opened_task(runtime, project.name, request.pr)
    branch, base = found.opened.branch, found.wave_branch
    fetch_branches(
        run_process, BranchesFetch(repository=worktree, branches=(base, branch), environment=ENVIRONMENT_OF_THE_RUN)
    )
    if check_ancestor(run_process, worktree, f"{REMOTE}/{base}", "HEAD").exit_code == NOT_AN_ANCESTOR:
        raise BrigadeError(f"{branch} does not descend from the head of {base}: rebase it first")
    push_with_lease(
        run_process,
        LeasedPush(
            worktree=worktree,
            branch=branch,
            expected_head=resolve_commit(run_process, worktree, f"{REMOTE}/{branch}"),
            environment=ENVIRONMENT_OF_THE_RUN,
        ),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": project.name,
        "pr": request.pr,
        "task": found.opened.task,
        "branch": branch,
        "base": base,
        "head": read_head(run_process, worktree),
    }


COMMAND = Command(
    path=("rebase", "done"),
    help="push the branch of the pull request of a task once it descends from the head of its base",
    group_help="put the pull request of a task back on its base",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=rebase_done,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
