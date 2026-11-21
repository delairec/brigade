from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import COMMIT_TIMEOUT_S, GIT_TIMEOUT_S, REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

REMOTE = "origin"


@dataclass(frozen=True)
class FilesPush:
    remote: str
    clone: Path
    tree: Path
    files: tuple[str, ...]
    message: str
    author_name: str
    author_email: str
    credential_helper: str
    environment: dict


def push_files_to_remote(run_process: Callable[[ProcessRequest], ProcessRecord], push: FilesPush) -> None:
    def run(argv: tuple[str, ...], timeout_s: float) -> None:
        run_process(ProcessRequest(argv=argv, cwd=str(push.tree), timeout_s=timeout_s, environment=push.environment))

    tree = ("--git-dir", str(push.clone), "--work-tree", str(push.tree))
    run(("git", "clone", "--bare", push.remote, str(push.clone)), REMOTE_TIMEOUT_S)
    run(("git", *tree, "add", *push.files), GIT_TIMEOUT_S)
    identity = ("-c", f"user.name={push.author_name}", "-c", f"user.email={push.author_email}")
    run(("git", *identity, *tree, "commit", "--message", push.message), COMMIT_TIMEOUT_S)
    credentials = ("-c", "credential.helper=", "-c", f"credential.helper={push.credential_helper}")
    run(("git", *credentials, *tree, "push", REMOTE, "HEAD"), REMOTE_TIMEOUT_S)
