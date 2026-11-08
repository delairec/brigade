import shutil
from pathlib import Path

from brigade.git.clear_worktree_path import clear_worktree_path
from tests.integration.repository_test_case import RepositoryTestCase
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


class ClearWorktreePathTest(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.worktree = Path(self.root.name) / "run" / "checkout"
        self.worktree.parent.mkdir()

    def add_worktree(self) -> None:
        run_git(self.repository, "worktree", "add", "--quiet", "--detach", str(self.worktree), "main")

    def assert_path_free(self) -> None:
        self.add_worktree()
        self.assertTrue((self.worktree / ".git").exists())

    def test_should_free_the_path_of_a_worktree_still_registered(self):
        # Arrange
        self.add_worktree()
        (self.worktree / "notes.txt").write_text("left by the attempt\n", encoding="utf-8")

        # Act
        clear_worktree_path(run_process_without_trail, self.repository, self.worktree)

        # Assert
        self.assert_path_free()

    def test_should_free_the_path_of_a_registered_worktree_whose_directory_is_gone(self):
        # Arrange
        self.add_worktree()
        shutil.rmtree(self.worktree)

        # Act
        clear_worktree_path(run_process_without_trail, self.repository, self.worktree)

        # Assert
        self.assert_path_free()

    def test_should_free_a_path_that_holds_a_directory_git_does_not_know(self):
        # Arrange
        self.worktree.mkdir()
        (self.worktree / "notes.txt").write_text("left by the attempt\n", encoding="utf-8")

        # Act
        clear_worktree_path(run_process_without_trail, self.repository, self.worktree)

        # Assert
        self.assert_path_free()

    def test_should_accept_a_path_nothing_occupies(self):
        # Act
        clear_worktree_path(run_process_without_trail, self.repository, self.worktree)

        # Assert
        self.assert_path_free()

    def test_should_leave_the_other_worktrees_of_the_repository_alone(self):
        # Arrange
        other = Path(self.root.name) / "other"
        run_git(self.repository, "worktree", "add", "--quiet", "--detach", str(other), "main")

        # Act
        clear_worktree_path(run_process_without_trail, self.repository, self.worktree)

        # Assert
        self.assertIn(str(other), run_git(self.repository, "worktree", "list", "--porcelain"))
