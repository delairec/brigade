from pathlib import Path

from tests.process_launcher import ProcessLauncher

PINNED_COMMIT_DATES = {"GIT_AUTHOR_DATE": "2026-10-12T09:00:00Z", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00Z"}


class TemporaryProject:
    def __init__(self, path: Path, environment: dict):
        self.path = path
        self.environment = environment
        path.mkdir(parents=True)
        self.run_git("init", "--quiet", "--initial-branch=main")

    def run_git(self, *arguments: str) -> str:
        completed = ProcessLauncher.run(
            ["git", "-C", str(self.path), *arguments],
            capture_output=True,
            text=True,
            check=True,
            env=self.environment,
        )
        return completed.stdout

    def write(self, relative_path: str, content: str = "") -> None:
        file = self.path / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)

    def track(self, *relative_paths: str) -> None:
        self.run_git("add", "--", *relative_paths)
