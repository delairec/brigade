import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.read_entities import Entity
from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA
from brigade.errors import BrigadeError
from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.create_branch import create_branch
from brigade.git.find_branch import find_branch
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.parse_configuration import CLI_KEY
from brigade.waves.locate_project_main import locate_project_main

BRANCH = "brigade/init-corpus"
WORKTREES_DIRECTORY = "corpus-installs"
SCHEMA_FILE = "_schema.awawa"
SUBJECT = "docs(corpus): install the schema of the project corpus"
PULL_REQUEST_BODY = "The awawa schema brigade needs to plan and deliver the tasks of this project."
NO_MILESTONE = None


@dataclass(frozen=True)
class CorpusInstallation:
    project: Entity
    forge: object
    read_environment: Callable[[str], dict]


def _commit_on_branch(runtime: Runtime, installation: CorpusInstallation, root: Path) -> None:
    project = installation.project
    worktree = runtime.paths.cache_root / WORKTREES_DIRECTORY / project.name
    main = locate_project_main(runtime.run_process, project, installation.read_environment)
    add_detached_worktree(runtime.run_process, root, worktree, main)
    try:
        change_corpus_file(
            runtime.run_process,
            CorpusChange(
                repository=worktree,
                lock=locate_corpus_lock(runtime.paths.lock_directory, root),
                file_names=(f"{read_project_field(project, 'CORPUS')}/{SCHEMA_FILE}",),
                describe_message=lambda: SUBJECT,
                rewrite=lambda texts: (SHIPPED_PROJECT_SCHEMA.read_text(encoding="utf-8"),),
            ),
        )
        create_branch(runtime.run_process, worktree, BRANCH)
    finally:
        remove_worktree(runtime.run_process, root, worktree)


def _open_pull_request(runtime: Runtime, installation: CorpusInstallation, root: Path) -> int:
    environment = installation.read_environment(CLI_KEY)
    push_branch(runtime.run_process, BranchPush(repository=root, branch=BRANCH, environment=environment))
    opened = installation.forge.open_pull_request(
        {
            "repository": str(root),
            "base": read_project_field(installation.project, "MAIN"),
            "branch": BRANCH,
            "title": SUBJECT,
            "body": PULL_REQUEST_BODY,
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        runtime,
    )
    return opened["number"]


def install_project_corpus(runtime: Runtime, installation: CorpusInstallation) -> dict:
    root = Path(read_project_field(installation.project, "PATH"))
    if find_branch(runtime.run_process, root, BRANCH):
        raise BrigadeError(f"the branch {BRANCH} already exists in {root}; merge it or delete it")
    _commit_on_branch(runtime, installation, root)
    if not is_on_a_forge(installation.project):
        return {
            "branch": BRANCH,
            "pull_request": None,
            "merge_command": shlex.join(("git", "-C", str(root), "merge", BRANCH)),
        }
    return {
        "branch": BRANCH,
        "pull_request": _open_pull_request(runtime, installation, root),
        "merge_command": None,
    }
