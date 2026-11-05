from dataclasses import dataclass

from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.git.reset_branch import reset_branch
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.locate_study_project import locate_study_project
from brigade.studies.mark_milestone_reached import mark_milestone_reached
from brigade.studies.present_answer import present_answer
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file

CORPUS_FIELD = "CORPUS"
MAIN_FIELD = "MAIN"
CHECKOUT_DIRECTORY = "checkout"
REMOTE_PREFIX = "origin/"
NO_PULL_REQUEST = None
NO_MILESTONE = None


PATH_FIELD = "PATH"


@dataclass(frozen=True)
class MilestonePublication:
    forge_name: str
    repository: str
    main: str
    markdown: str
    environment: dict


def _find_opened_pull_request(context: StudyRunContext) -> int | None:
    order = context.study.milestone
    opened = [
        entry.event.pr
        for entry in read_ledger(context.runtime.paths.state_root).entries
        if isinstance(entry.event, MilestonePrOpened)
        and entry.event.project == order.project
        and entry.event.milestone == order.milestone
    ]
    return opened[-1] if opened else NO_PULL_REQUEST


def _open_pull_request(context: StudyRunContext, publication: MilestonePublication) -> int:
    order = context.study.milestone
    forge = context.equipment.resolve_forge(publication.forge_name)
    opened = forge.open_pull_request(
        {
            "repository": publication.repository,
            "base": publication.main,
            "branch": order.branch,
            "title": f"chore(milestone): merge the milestone {order.milestone} into {publication.main}",
            "body": publication.markdown,
            "milestone": NO_MILESTONE,
            "environment": publication.environment,
        },
        context.runtime,
    )
    login = ask_forge_account(forge, publication.forge_name, publication.environment, context.runtime).login
    append_event(
        context.runtime.paths,
        context.runtime.now,
        MilestonePrOpened(project=order.project, milestone=order.milestone, pr=opened["number"], login=login),
    )
    return opened["number"]


def _publish_pull_request(context: StudyRunContext, publication: MilestonePublication, checkout) -> int:
    opened = _find_opened_pull_request(context)
    if opened is None:
        return _open_pull_request(context, publication)
    body = {
        "repository": str(checkout),
        "number": opened,
        "body": publication.markdown,
        "environment": publication.environment,
    }
    context.equipment.resolve_forge(publication.forge_name).rewrite_pull_request_body(body, context.runtime)
    return opened


def _commit_report(context: StudyRunContext, publication: MilestonePublication, report: str, checkout) -> None:
    run_process = context.runtime.run_process
    branch = context.study.milestone.branch
    reset_branch(run_process, checkout, branch)
    create_directory((checkout / report).parent)
    write_text_file(checkout / report, publication.markdown)
    commit_files(
        run_process,
        CommitRequest(
            repository=checkout,
            files=(report,),
            message=f"docs(milestones): add the report of {context.study.milestone.milestone}",
        ),
    )
    mark_milestone_reached(context.runtime, checkout, context.study.milestone.milestone)
    push_branch(run_process, BranchPush(repository=checkout, branch=branch, environment=publication.environment))


def publish_milestone_report(context: StudyRunContext) -> dict:
    located = locate_study_project(context)
    environment = read_publication_environment(context, located)
    project = find_project(read_projects(context.runtime), context.study.project)
    run_process = context.runtime.run_process
    order = context.study.milestone
    report = f"{read_project_field(project, CORPUS_FIELD)}/milestones/{order.milestone}-report.md"
    publication = MilestonePublication(
        forge_name=located.forge,
        repository=read_project_field(project, PATH_FIELD),
        main=read_project_field(project, MAIN_FIELD),
        markdown=present_answer(context).markdown,
        environment=environment,
    )
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    fetch_branches(
        run_process, BranchesFetch(repository=located.path, branches=(order.branch,), environment=environment)
    )
    add_detached_worktree(run_process, located.path, checkout, f"{REMOTE_PREFIX}{order.branch}")
    try:
        _commit_report(context, publication, report, checkout)
        pull_request = (
            NO_PULL_REQUEST if located.forge is None else _publish_pull_request(context, publication, checkout)
        )
    finally:
        remove_worktree(run_process, located.path, checkout)
    return {"report": report, "branch": order.branch, "pull_request": pull_request}
