from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.open_branch_worktree import open_branch_worktree
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.read_head import read_head
from brigade.git.remove_worktree import remove_worktree
from brigade.git.reset_branch import reset_branch
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_pr_described import MilestonePrDescribed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.locate_study_project import StudyProject, locate_study_project
from brigade.studies.mark_milestone_reached import mark_milestone_reached
from brigade.studies.present_answer import present_answer
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.waves.compose_milestone_title import MilestoneTitleDemand, compose_milestone_title
from brigade.waves.locate_branch_worktree import locate_branch_worktree

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
    project: Entity
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


def _open_pull_request(context: StudyRunContext, publication: MilestonePublication, checkout) -> int:
    order = context.study.milestone
    forge = context.equipment.resolve_forge(publication.forge_name)
    opened = forge.open_pull_request(
        {
            "repository": publication.repository,
            "base": publication.main,
            "branch": order.branch,
            "title": compose_milestone_title(
                MilestoneTitleDemand(run_process=context.runtime.run_process, root=checkout, milestone=order.milestone)
            ),
            "body": publication.markdown,
            "milestone": NO_MILESTONE,
            "environment": publication.environment,
        },
        context.runtime,
    )
    login = ask_forge_account(forge, publication.forge_name, publication.environment, context.runtime).login
    _record_opening(context, MilestonePrOpened(order.project, order.milestone, opened["number"], login), checkout)
    return opened["number"]


def _record_opening(context: StudyRunContext, opening: MilestonePrOpened, checkout) -> None:
    append_event(context.runtime.paths, context.runtime.now, opening)
    append_event(
        context.runtime.paths,
        context.runtime.now,
        MilestonePrDescribed(
            project=opening.project,
            milestone=opening.milestone,
            pr=opening.pr,
            head=read_head(context.runtime.run_process, checkout),
            login=opening.login,
        ),
    )


def _publish_pull_request(context: StudyRunContext, publication: MilestonePublication, checkout) -> int:
    opened = _find_opened_pull_request(context)
    if opened is None:
        return _open_pull_request(context, publication, checkout)
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
    mark_milestone_reached(context.runtime, checkout, publication.project, context.study.milestone.milestone)
    if publication.forge_name is not None:
        push_branch(run_process, BranchPush(repository=checkout, branch=branch, environment=publication.environment))


def _open_branch_of_the_clone(context: StudyRunContext, located: StudyProject) -> Path:
    branch = context.study.milestone.branch
    worktree_root = context.equipment.collector_equipment.configuration.worktree_root
    worktree = BranchWorktree(
        path=locate_branch_worktree(located.path, worktree_root, branch), branch=branch, start=branch
    )
    open_branch_worktree(context.runtime.run_process, located.path, worktree)
    return worktree.path


def _open_detached_checkout(context: StudyRunContext, located: StudyProject, environment: dict) -> Path:
    run_process = context.runtime.run_process
    branch = context.study.milestone.branch
    fetch_branches(run_process, BranchesFetch(repository=located.path, branches=(branch,), environment=environment))
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    add_detached_worktree(run_process, located.path, checkout, f"{REMOTE_PREFIX}{branch}")
    return checkout


def _publish_on_the_clone(context: StudyRunContext, publication: MilestonePublication, report: str, located) -> None:
    checkout = _open_branch_of_the_clone(context, located)
    _commit_report(context, publication, report, checkout)


def _publish_on_the_forge(
    context: StudyRunContext, publication: MilestonePublication, report: str, located: StudyProject
) -> int:
    run_process = context.runtime.run_process
    checkout = _open_detached_checkout(context, located, publication.environment)
    try:
        _commit_report(context, publication, report, checkout)
        return _publish_pull_request(context, publication, checkout)
    finally:
        remove_worktree(run_process, located.path, checkout)


def publish_milestone_report(context: StudyRunContext) -> dict:
    located = locate_study_project(context)
    environment = read_publication_environment(context, located)
    project = find_project(read_projects(context.runtime), context.study.project)
    order = context.study.milestone
    report = f"{read_project_field(project, CORPUS_FIELD)}/milestones/{order.milestone}-report.md"
    publication = MilestonePublication(
        forge_name=located.forge,
        repository=read_project_field(project, PATH_FIELD),
        main=read_project_field(project, MAIN_FIELD),
        project=project,
        markdown=present_answer(context).markdown,
        environment=environment,
    )
    if located.forge is None:
        _publish_on_the_clone(context, publication, report, located)
        return {"report": report, "branch": order.branch, "pull_request": NO_PULL_REQUEST}
    pull_request = _publish_on_the_forge(context, publication, report, located)
    return {"report": report, "branch": order.branch, "pull_request": pull_request}
