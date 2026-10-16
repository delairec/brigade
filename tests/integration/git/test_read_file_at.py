import tempfile
import unittest
from pathlib import Path

from brigade.git.read_file_at import read_file_at
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

IDENTITY = ("-c", "user.name=Ada Lovelace", "-c", "user.email=ada@example.org")


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class ReadFileAtTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        (self.repository / ".gitignore").write_text("build/\n")
        run_git(self.repository, "add", ".gitignore")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "-m", "first")

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_file_at_a_location_and_nothing_where_it_is_absent(self):
        for location, expected in [("main:.gitignore", "build/\n"), ("main:absent.txt", "")]:
            with self.subTest(location=location):
                # Act
                content = read_file_at(run_process_without_trail, self.repository, location)

                # Assert
                self.assertEqual(content, expected)
