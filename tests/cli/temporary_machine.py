import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLONE_ENTRY_POINT = REPOSITORY_ROOT / "bin" / "brigade"
SHIPPED_SCHEMA = REPOSITORY_ROOT / "brigade" / "corpus" / "data" / "schema.awawa.tpl"
USER_IDENTITY = "[user]\n\tname = Ada Lovelace\n\temail = ada@example.org\n"


class TemporaryMachine:
    def __init__(self, root: Path, git_configuration: str = USER_IDENTITY):
        self.home = root / "home"
        self.config_home = root / "config"
        self.state_home = root / "state"
        self.cache_home = root / "cache"
        self.corpus = self.config_home / "brigade"
        self.home.mkdir()
        (self.home / ".gitconfig").write_text(git_configuration)

    def describe_environment(self) -> dict:
        return {
            "PATH": os.environ["PATH"],
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.config_home),
            "XDG_STATE_HOME": str(self.state_home),
            "XDG_CACHE_HOME": str(self.cache_home),
        }

    def run_brigade(self, entry_point: Path, *arguments: str, environment: dict | None = None):
        return subprocess.run(
            [sys.executable, str(entry_point), *arguments],
            capture_output=True,
            text=True,
            env=environment or self.describe_environment(),
        )

    def run_init(self, *options: str):
        return self.run_brigade(CLONE_ENTRY_POINT, "init", *options)

    def read_git(self, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.corpus), *arguments],
            capture_output=True,
            text=True,
            check=True,
            env=self.describe_environment(),
        )
        return completed.stdout
