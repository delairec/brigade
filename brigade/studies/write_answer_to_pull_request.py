from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.add_detached_worktree import DetachedWorktree, add_detached_worktree
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import REMOTE, BranchesFetch, fetch_branches
from brigade.git.push_branch import BranchPush
from brigade.git.push_head_to_branch import push_head_to_branch
from brigade.git.remove_detached_worktree import remove_detached_worktree
from brigade.studies.locate_study_project import locate_study_project
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file

PULL_REQUEST_FILE_OUTPUT_PREFIX = "pr-file:"
NUMBER_SEPARATOR = ":"
WRITING_REASON = "brigade writing an answer on a pull request"
CHECKOUT_DIRECTORY = "checkout"


@dataclass(frozen=True)
class AnswerCommit:
    checkout: Path
    relative_path: str
    markdown: str


def _commit_answer(context: StudyRunContext, answer: AnswerCommit) -> None:
    create_directory((answer.checkout / answer.relative_path).parent)
    write_text_file(answer.checkout / answer.relative_path, answer.markdown)
    commit_files(
        context.runtime.run_process,
        CommitRequest(
            repository=answer.checkout,
            files=(answer.relative_path,),
            message=f"docs(reports): add the answer of {context.study.name}, run {context.run_id}",
        ),
    )


def write_answer_to_pull_request(context: StudyRunContext, publication: AnswerPublication) -> dict:
    project = locate_study_project(context)
    if project.forge is None:
        raise BrigadeError(f"the output {context.study.output} needs a project with a forge")
    number, _, relative_path = context.study.output.removeprefix(PULL_REQUEST_FILE_OUTPUT_PREFIX).partition(
        NUMBER_SEPARATOR
    )
    run_process = context.runtime.run_process
    environment = read_publication_environment(context, project)
    query = PullRequestDetailsQuery(repository=str(project.path), number=int(number), environment=environment)
    forge = context.equipment.resolve_forge(project.forge)
    head = ask_pull_request_details(forge, project.forge, query, context.runtime)["head"]
    fetch_branches(run_process, BranchesFetch(repository=project.path, branches=(head,), environment=environment))
    checkout = context.run_directory / CHECKOUT_DIRECTORY
    worktree = DetachedWorktree(repository=project.path, path=checkout, start=f"{REMOTE}/{head}", reason=WRITING_REASON)
    add_detached_worktree(run_process, worktree)
    try:
        _commit_answer(context, AnswerCommit(checkout, relative_path, publication.markdown))
        push_head_to_branch(run_process, BranchPush(repository=checkout, branch=head, environment=environment))
    finally:
        remove_detached_worktree(run_process, worktree)
    return {"branch": head, "pull_request": int(number)}
