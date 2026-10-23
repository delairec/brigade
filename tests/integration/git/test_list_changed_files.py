import tempfile
import unittest
from pathlib import Path

from brigade.git.list_changed_files import list_changed_files
from tests.integration.repository_test_case import IDENTITY
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class ListChangedFilesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name)
        run_git(self.repository, "init", "--quiet")
        (self.repository / "cart.py").write_text("committed\n")
        (self.repository / "billing.py").write_text("committed\n")
        run_git(self.repository, "add", "cart.py", "billing.py")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "-m", "first")

    def tearDown(self):
        self.root.cleanup()

    def test_should_answer_no_file_for_a_worktree_identical_to_head(self):
        # Arrange
        no_changed_file = ()

        # Act
        changed = list_changed_files(run_process_without_trail, self.repository)

        # Assert
        self.assertEqual(changed, no_changed_file)

    def test_should_name_the_modified_the_staged_and_the_untracked_files(self):
        # Arrange
        (self.repository / "cart.py").write_text("edited\n")
        (self.repository / "billing.py").write_text("staged\n")
        run_git(self.repository, "add", "billing.py")
        (self.repository / "shipping file.py").write_text("new\n")

        # Act
        changed = list_changed_files(run_process_without_trail, self.repository)

        # Assert
        self.assertEqual(changed, ("billing.py", "cart.py", "shipping file.py"))

    def test_should_name_both_paths_of_a_renamed_file(self):
        # Arrange
        run_git(self.repository, "mv", "cart.py", "basket.py")

        # Act
        changed = list_changed_files(run_process_without_trail, self.repository)

        # Assert
        self.assertEqual(changed, ("basket.py", "cart.py"))
