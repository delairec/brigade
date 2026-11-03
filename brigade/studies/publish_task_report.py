from dataclasses import dataclass
from pathlib import Path

from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.push_ref_to_branch import RefPush, push_ref_to_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.locate_study_project import locate_study_project
from brigade.studies.present_answer import present_answer
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file

CORPUS_FIELD = "CORPUS"
CHECKOUT_DIRECTORY = "checkout"
REMOTE_PREFIX = "origin/"
DETACHED_HEAD = "HEAD"
NO_PULL_REQUEST = None


@dataclass(frozen=True)
class TaskPublication:
    forge_name: str | None
    checkout: Path
    report: str
    markdown: str
    environment: dict


def _find_task_pull_request(context: StudyRunContext) -> int:
    order = context.study.task
    return [
        entry.event.pr
        for entry in read_ledger(context.runtime.paths.state_root).entries
        if isinstance(entry.event, TaskPrOpened)
        and (entry.event.project, entry.event.task, entry.event.wave) == (order.project, order.task, order.wave)
    ][-1]


def _commit_report(context: StudyRunContext, publication: TaskPublication) -> None:
    run_process = context.runtime.run_process
    order = context.study.task
    checkout = publication.checkout
    create_directory((checkout / publication.report).parent)
    write_text_file(checkout / publication.report, publication.markdown)
    commit_files(
        run_process,
        CommitRequest(
            repository=checkout, files=(publication.report,), message=f"docs(tasks): add the report of {order.task}"
        ),
    )
    push_ref_to_branch(
        run_process,
        RefPush(repository=checkout, ref=DETACHED_HEAD, branch=order.branch, environment=publication.environment),
    )


def _replace_pull_request_body(context: StudyRunContext, publication: TaskPublication) -> int:
    number = _find_task_pull_request(context)
    body = {
        "repository": str(publication.checkout),
        "number": number,
        "body": publication.markdown,
        "environment": publication.environment,
    }
    context.equipment.resolve_forge(publication.forge_name).rewrite_pull_request_body(body, context.runtime)
    return number


def publish_task_report(context: StudyRunContext) -> dict:
    located = locate_study_project(context)
    environment = read_publication_environment(context, located)
    project = find_project(read_projects(context.runtime), context.study.project)
    run_process = context.runtime.run_process
    order = context.study.task
    report = f"{read_project_field(project, CORPUS_FIELD)}/tasks/{order.task}-report.md"
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    publication = TaskPublication(
        forge_name=located.forge,
        checkout=checkout,
        report=report,
        markdown=present_answer(context).markdown,
        environment=environment,
    )
    fetch_branches(
        run_process, BranchesFetch(repository=located.path, branches=(order.branch,), environment=environment)
    )
    add_detached_worktree(run_process, located.path, checkout, f"{REMOTE_PREFIX}{order.branch}")
    try:
        _commit_report(context, publication)
        pull_request = NO_PULL_REQUEST if located.forge is None else _replace_pull_request_body(context, publication)
    finally:
        remove_worktree(run_process, located.path, checkout)
    return {"report": report, "branch": order.branch, "pull_request": pull_request}
