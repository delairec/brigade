import tempfile
import unittest
from pathlib import Path

from brigade.git.restore_files import restore_files
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


class RestoreFilesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name)
        run_git(self.repository, "init", "--quiet")
        (self.repository / "projects.awawa").write_text("committed\n")
        run_git(self.repository, "add", "projects.awawa")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "-m", "first")

    def tearDown(self):
        self.root.cleanup()

    def test_should_put_back_the_committed_content_of_a_tracked_file(self):
        # Arrange
        (self.repository / "projects.awawa").write_text("edited\n")

        # Act
        restore_files(run_process_without_trail, self.repository, ("projects.awawa",))

        # Assert
        self.assertEqual(
            ((self.repository / "projects.awawa").read_text(), run_git(self.repository, "status", "--porcelain")),
            ("committed\n", ""),
        )

    def test_should_remove_a_file_the_repository_does_not_hold(self):
        # Arrange
        (self.repository / "policies.awawa").write_text("new\n")

        # Act
        restore_files(run_process_without_trail, self.repository, ("policies.awawa",))

        # Assert
        self.assertEqual(
            ((self.repository / "policies.awawa").exists(), run_git(self.repository, "status", "--porcelain")),
            (False, ""),
        )
