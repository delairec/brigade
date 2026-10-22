from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.git.reset_branch import reset_branch
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.locate_study_project import locate_study_project
from brigade.studies.present_answer import present_answer
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.waves.find_integration_pull_request import find_integration_pull_request
from brigade.waves.find_wave_started import find_wave_started

CORPUS_FIELD = "CORPUS"
WAVE_NUMBER_SEPARATOR = "_w"
CHECKOUT_DIRECTORY = "checkout"
REMOTE_PREFIX = "origin/"
UNBOUND_ENVIRONMENT = {}
NO_PULL_REQUEST = None


def _locate_report(context: StudyRunContext) -> str:
    project = find_project(read_projects(context.runtime), context.study.project)
    wave_number = context.study.wave.rsplit(WAVE_NUMBER_SEPARATOR, 1)[1]
    return f"{read_project_field(project, CORPUS_FIELD)}/waves/{wave_number}-report.md"


def publish_wave_report(context: StudyRunContext) -> dict:
    project = locate_study_project(context)
    run_process = context.runtime.run_process
    wave = context.study.wave
    events = tuple(entry.event for entry in read_ledger(context.runtime.paths.state_root).entries)
    branch = find_wave_started(events, wave).branch
    report = _locate_report(context)
    markdown = present_answer(context).markdown
    pull_request = find_integration_pull_request(events, wave) if project.forge is not None else NO_PULL_REQUEST
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    fetch_branches(
        run_process, BranchesFetch(repository=project.path, branches=(branch,), environment=UNBOUND_ENVIRONMENT)
    )
    add_detached_worktree(run_process, project.path, checkout, f"{REMOTE_PREFIX}{branch}")
    try:
        reset_branch(run_process, checkout, branch)
        create_directory((checkout / report).parent)
        write_text_file(checkout / report, markdown)
        commit_files(
            run_process,
            CommitRequest(repository=checkout, files=(report,), message=f"docs(waves): add the report of {wave}"),
        )
        push_branch(run_process, BranchPush(repository=checkout, branch=branch, environment=UNBOUND_ENVIRONMENT))
        if pull_request is not None:
            context.equipment.resolve_forge(project.forge).rewrite_pull_request_body(
                {
                    "repository": str(checkout),
                    "number": pull_request,
                    "body": markdown,
                    "environment": UNBOUND_ENVIRONMENT,
                },
                context.runtime,
            )
    finally:
        remove_worktree(run_process, project.path, checkout)
    return {"report": report, "branch": branch, "pull_request": pull_request}
