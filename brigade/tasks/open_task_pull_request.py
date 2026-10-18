import json
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.read_current_branch import read_current_branch
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_created import MilestoneCreated
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.tasks.compose_pull_request_title import PullRequestTitleParts, compose_pull_request_title
from brigade.tasks.describe_pull_request_body import PullRequestBodyParts, describe_pull_request_body
from brigade.tasks.locate_check_record import locate_check_record
from brigade.tasks.locate_task_worktree import TaskWorktree, locate_task_worktree
from brigade.waves.require_wave_name import require_wave_name

DOCUMENT_SCHEMA_VERSION = 1
HEAD = "HEAD"
MILESTONE_PREFIX = "@MILESTONE."


@dataclass(frozen=True)
class TaskPullRequestDemand:
    path: Path
    task: str | None
    subject: str | None
    forge: object
    environment: dict
    login: str
    attribution: tuple[str, ...]


@dataclass(frozen=True)
class ForgeSession:
    worktree: TaskWorktree
    forge: object
    environment: dict
    login: str


def _require_passing_check(runtime: Runtime, worktree: TaskWorktree) -> dict:
    target = f"@TASK.{worktree.task}"
    record = locate_check_record(runtime.paths.state_root, worktree.project.name, worktree.task)
    if not record.exists():
        raise BrigadeError(f"no check of {target} is recorded; run brigade task check")
    check = json.loads(record.read_text(encoding="utf-8"))
    head = resolve_commit(runtime.run_process, worktree.path, HEAD)
    if check["head"] != head:
        raise BrigadeError(
            f"the last check of {target} is of {check['head']}, not of HEAD {head}; run brigade task check"
        )
    failing = next((entry["command"] for entry in check["checks"] if not entry["passed"]), None)
    if failing is not None:
        raise BrigadeError(f"the last check of {target} failed on {failing}; run brigade task check")
    return check


def _compose_title(task: Entity, subject: str | None) -> str:
    task_type = read_project_field(task, "TYPE")
    if task_type is None:
        raise BrigadeError(f"@TASK.{task.name} carries no TYPE, which the title of its pull request opens on")
    return compose_pull_request_title(
        PullRequestTitleParts(
            type=task_type, component=read_project_field(task, "COMPONENT"), subject=subject, task=task.name
        )
    )


def _read_milestone_title(runtime: Runtime, worktree: TaskWorktree, task: Entity) -> str:
    milestone = read_project_field(task, "MILESTONE")
    if milestone is None:
        raise BrigadeError(
            f"@TASK.{task.name} carries no MILESTONE, whose TITLE names the milestone of its pull request"
        )
    milestone = milestone.removeprefix(MILESTONE_PREFIX)
    return read_project_field(read_entity(runtime.run_process, worktree.path, "MILESTONE", milestone), "TITLE")


def _ensure_milestone(runtime: Runtime, session: ForgeSession, title: str) -> None:
    request = {"repository": str(session.worktree.path), "environment": session.environment, "title": title}
    if title in session.forge.list_milestones(request, runtime)["titles"]:
        return
    session.forge.create_milestone(request, runtime)
    append_event(
        runtime.paths,
        runtime.now,
        MilestoneCreated(project=session.worktree.project.name, title=title, login=session.login),
    )


def open_task_pull_request(runtime: Runtime, demand: TaskPullRequestDemand) -> dict:
    worktree = locate_task_worktree(runtime, demand.path, demand.task)
    check = _require_passing_check(runtime, worktree)
    wave = require_wave_name(
        tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries), worktree.wave
    )
    task = read_entity(runtime.run_process, worktree.path, "TASK", worktree.task)
    title = _compose_title(task, demand.subject)
    session = ForgeSession(worktree=worktree, forge=demand.forge, environment=demand.environment, login=demand.login)
    branch = read_current_branch(runtime.run_process, worktree.path)
    milestone = _read_milestone_title(runtime, worktree, task)
    push_branch(
        runtime.run_process, BranchPush(repository=worktree.path, branch=branch, environment=demand.environment)
    )
    _ensure_milestone(runtime, session, milestone)
    body = describe_pull_request_body(
        PullRequestBodyParts(
            title=read_project_field(task, "TITLE"),
            specs=tuple(field.value for field in task.fields if field.name == "SPEC"),
            check=check,
            attribution=demand.attribution,
        )
    )
    pull_request = demand.forge.open_pull_request(
        {
            "repository": str(worktree.path),
            "base": worktree.wave["branch"],
            "branch": branch,
            "title": title,
            "body": body,
            "milestone": milestone,
            "environment": demand.environment,
        },
        runtime,
    )
    append_event(
        runtime.paths,
        runtime.now,
        TaskPrOpened(
            project=worktree.project.name,
            task=worktree.task,
            wave=wave,
            branch=branch,
            pr=pull_request["number"],
            login=session.login,
        ),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": worktree.project.name,
        "task": worktree.task,
        "branch": branch,
        "base": worktree.wave["branch"],
        "title": title,
        "milestone": milestone,
        "pr": pull_request["number"],
        "url": pull_request["url"],
        "login": session.login,
    }
