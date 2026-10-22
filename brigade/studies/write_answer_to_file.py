from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.force_push_branch import force_push_branch
from brigade.git.push_branch import BranchPush
from brigade.git.read_main_branch import read_main_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.git.reset_branch import reset_branch
from brigade.studies.locate_study_project import StudyProject, locate_study_project
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file

FILE_OUTPUT_PREFIX = "file:"
RUN_PLACEHOLDER = "{run}"
BRANCH_PREFIX = "brigade/study-"
CHECKOUT_DIRECTORY = "checkout"
NO_PULL_REQUEST = None
NO_MILESTONE = None


def _open_pull_request(
    context: StudyRunContext, project: StudyProject, branch: str, base: str, publication: AnswerPublication
) -> str | None:
    if project.forge is None:
        return NO_PULL_REQUEST
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    environment = read_publication_environment(context, project)
    force_push_branch(
        context.runtime.run_process, BranchPush(repository=checkout, branch=branch, environment=environment)
    )
    forge = context.equipment.resolve_forge(project.forge)
    pull_request = forge.open_pull_request(
        {
            "repository": str(checkout),
            "base": base,
            "branch": branch,
            "title": publication.title,
            "body": publication.markdown,
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        context.runtime,
    )
    return pull_request["url"]


def write_answer_to_file(context: StudyRunContext, publication: AnswerPublication) -> dict:
    project = locate_study_project(context)
    run_process = context.runtime.run_process
    relative_path = context.study.output.removeprefix(FILE_OUTPUT_PREFIX).replace(RUN_PLACEHOLDER, context.run_id)
    branch = f"{BRANCH_PREFIX}{context.study.name}-{context.run_id}"
    base = read_main_branch(run_process, project.path)
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    add_detached_worktree(run_process, project.path, checkout, base)
    try:
        reset_branch(run_process, checkout, branch)
        create_directory((checkout / relative_path).parent)
        write_text_file(checkout / relative_path, publication.markdown)
        commit_files(
            run_process,
            CommitRequest(
                repository=checkout,
                files=(relative_path,),
                message=f"docs(studies): add the answer of {context.study.name}, run {context.run_id}",
            ),
        )
        pull_request = _open_pull_request(context, project, branch, base, publication)
    finally:
        remove_worktree(run_process, project.path, checkout)
    return {"branch": branch, "pull_request": pull_request}
