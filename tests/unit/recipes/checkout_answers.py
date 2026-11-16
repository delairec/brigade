from pathlib import Path

from tests.unit.recording_process_runner import ProcessAnswer


def create_checkout_answers(worktree: Path, main_checkout: Path) -> dict:
    return {
        ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout=f"{worktree}\n"),
        ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
            stdout=f"{main_checkout / '.git'}\n"
        ),
    }
