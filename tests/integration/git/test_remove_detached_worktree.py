from pathlib import Path

from brigade.git.add_detached_worktree import DetachedWorktree, add_detached_worktree
from brigade.git.remove_detached_worktree import remove_detached_worktree
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


class RemoveDetachedWorktreeTest(RepositoryTestCase):
    def test_should_list_the_worktree_locked_with_its_reason_while_its_command_works(self):
        # Arrange
        worktree = DetachedWorktree(
            repository=self.repository,
            path=Path(self.root.name) / "cache" / "plans" / "R1",
            start="main",
            reason="brigade plan record",
        )

        # Act
        add_detached_worktree(run_process_without_trail, worktree)

        # Assert
        self.assertIn("locked brigade plan record\n", run_git(self.repository, "worktree", "list", "--porcelain"))

    def test_should_remove_the_locked_worktree_and_its_untracked_files(self):
        # Arrange
        worktree = DetachedWorktree(
            repository=self.repository,
            path=Path(self.root.name) / "cache" / "plans" / "R1",
            start="main",
            reason="brigade plan record",
        )
        add_detached_worktree(run_process_without_trail, worktree)
        (worktree.path / "plan.awawa").write_text("left by the planner\n")

        # Act
        remove_detached_worktree(run_process_without_trail, worktree)

        # Assert
        self.assertEqual(run_git(self.repository, "worktree", "list", "--porcelain").count("worktree "), 1)
