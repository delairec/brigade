import subprocess
from pathlib import Path


class TemporaryProject:
    def __init__(self, path: Path, environment: dict):
        self.path = path
        self.environment = environment
        path.mkdir(parents=True)
        self.run_git("init", "--quiet", "--initial-branch=main")

    def run_git(self, *arguments: str) -> str:
        completed = subprocess.run(  # noqa: S603 - the test's own command line
            ["git", "-C", str(self.path), *arguments],  # noqa: S607 - git found on the PATH of the test
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
