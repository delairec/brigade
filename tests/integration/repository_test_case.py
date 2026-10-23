import tempfile
import unittest
from pathlib import Path

from tests.process_launcher import ProcessLauncher

IDENTITY = ("-c", "user.name=Ada Lovelace", "-c", "user.email=ada@example.org")


def _run_git(repository: Path, *arguments: str) -> None:
    ProcessLauncher.run(["git", "-C", str(repository), *arguments], capture_output=True, check=True)


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        _run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        _run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "first")

    def tearDown(self):
        self.root.cleanup()
