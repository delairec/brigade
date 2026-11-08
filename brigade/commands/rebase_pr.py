import argparse
from dataclasses import dataclass
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_attribution import read_attribution
from brigade.commands._read_forge_environment import FORGE_KIND, ForgeSlot, read_forge_environment
from brigade.commands._repair_red_head import REBASE_SLOT
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.read_current_branch import read_current_branch
from brigade.git.read_head_subject import read_head_subject
from brigade.ledger.append_event import append_event
from brigade.ledger.repair_pr_opened import RepairPrOpened
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
NO_MILESTONE = None


def _render_text(document: dict) -> str:
    return document["url"]


def _compose_body(into: str, branch: str, attribution: list[str]) -> str:
    closing = "".join(f"{line}\n" for line in attribution)
    return f"Repairs the red head of {into} on {branch}.\n" + (f"\n{closing}" if closing else "")


@dataclass(frozen=True)
class _RepairSession:
    worktree: Path
    project: str
    forge: object
    environment: dict
    login: str


def _open_session(runtime: Runtime) -> tuple[_RepairSession, Configuration]:
    worktree = locate_worktree_root(runtime.run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, worktree))
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    forge_name = read_project_forge(project)
    forge = runtime.resolve_plugin(FORGE_KIND, forge_name)
    environment = read_forge_environment(configuration, ForgeSlot(forge_name, REBASE_SLOT), runtime)
    login = ask_forge_account(forge, forge_name, environment, runtime).login
    session = _RepairSession(worktree=worktree, project=project.name, forge=forge, environment=environment, login=login)
    return session, configuration


def rebase_pr(request: argparse.Namespace, runtime: Runtime) -> dict:
    session, configuration = _open_session(runtime)
    branch = read_current_branch(runtime.run_process, session.worktree)
    title = read_head_subject(runtime.run_process, session.worktree)
    push_branch(
        runtime.run_process, BranchPush(repository=session.worktree, branch=branch, environment=session.environment)
    )
    pull_request = session.forge.open_pull_request(
        {
            "repository": str(session.worktree),
            "base": request.into,
            "branch": branch,
            "title": title,
            "body": _compose_body(request.into, branch, read_attribution(configuration, runtime)),
            "milestone": NO_MILESTONE,
            "environment": session.environment,
        },
        runtime,
    )
    opened = RepairPrOpened(
        project=session.project, branch=branch, into=request.into, pr=pull_request["number"], login=session.login
    )
    append_event(runtime.paths, runtime.now, opened)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **opened.to_document(),
        "title": title,
        "url": pull_request["url"],
    }


COMMAND = Command(
    path=("rebase", "pr"),
    help=(
        "push the branch repairing a red main branch and open its pull request into that main branch,"
        " as the login of the rebase slot"
    ),
    group_help="put the pull request of a task back on its base",
    arguments=(Argument(("--into",), {"required": True, "help": "the main branch the repair goes into"}),),
    run=rebase_pr,
    render_text=_render_text,
)
