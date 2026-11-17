from pathlib import Path

from tests.unit.recording_process_runner import ProcessAnswer

NOT_A_REPOSITORY = ProcessAnswer(exit_code=128, stderr="fatal: not a git repository\n")


def create_checkout_answers(worktree: Path, main_checkout: Path) -> dict:
    return {
        ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout=f"{worktree}\n"),
        ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
            stdout=f"{main_checkout / '.git'}\n"
        ),
    }


def create_outside_repository_answers() -> dict:
    return {
        ("git", "rev-parse", "--git-dir"): NOT_A_REPOSITORY,
        ("git", "rev-parse", "--show-toplevel"): NOT_A_REPOSITORY,
        ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): NOT_A_REPOSITORY,
    }
