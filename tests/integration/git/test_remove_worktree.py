from pathlib import Path

from brigade.git.remove_worktree import remove_worktree
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


class RemoveWorktreeTest(RepositoryTestCase):
    def test_should_remove_the_worktree_and_its_untracked_files_from_the_repository(self):
        # Arrange
        worktree = Path(self.root.name) / "worktrees" / "S3"
        run_git(self.repository, "worktree", "add", "--quiet", "-b", "task/M1-empty-cart/S3", str(worktree))
        (worktree / "notes.txt").write_text("left by the run\n")

        # Act
        remove_worktree(run_process_without_trail, self.repository, worktree)

        # Assert
        self.assertFalse(worktree.exists())
        self.assertEqual(run_git(self.repository, "worktree", "list", "--porcelain").count("worktree "), 1)
