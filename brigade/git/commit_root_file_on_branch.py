from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0
ENTRY_SEPARATOR = "\0"
PATH_SEPARATOR = "\t"
REGULAR_FILE_MODE = "100644"


@dataclass(frozen=True)
class RootFileCommit:
    branch: str
    path: str
    content: str
    message: str


def _ask_git(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, argv: tuple, stdin: str | None = None
) -> str:
    record = run_process(ProcessRequest(argv=("git", *argv), cwd=str(repository), timeout_s=GIT_TIMEOUT_S, stdin=stdin))
    return record.stdout.strip(ENTRY_SEPARATOR).strip()


def _list_other_entries(tree_listing: str, path: str) -> list[str]:
    return [
        entry for entry in tree_listing.split(ENTRY_SEPARATOR) if entry and entry.split(PATH_SEPARATOR, 1)[1] != path
    ]


def commit_root_file_on_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, commit: RootFileCommit
) -> None:
    reference = f"refs/heads/{commit.branch}"
    parent = _ask_git(run_process, repository, ("rev-parse", "--verify", reference))
    blob = _ask_git(run_process, repository, ("hash-object", "-w", "--stdin"), commit.content)
    entries = [
        *_list_other_entries(_ask_git(run_process, repository, ("ls-tree", "-z", parent)), commit.path),
        f"{REGULAR_FILE_MODE} blob {blob}{PATH_SEPARATOR}{commit.path}",
    ]
    tree = _ask_git(
        run_process, repository, ("mktree", "-z"), "".join(f"{entry}{ENTRY_SEPARATOR}" for entry in entries)
    )
    created = _ask_git(run_process, repository, ("commit-tree", tree, "-p", parent, "-m", commit.message))
    _ask_git(run_process, repository, ("update-ref", reference, created, parent))
