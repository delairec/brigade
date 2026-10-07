import unittest
from pathlib import Path

from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.system.run_process import ProcessRecord


def record_of(stdout: str) -> ProcessRecord:
    return ProcessRecord(argv=("git",), cwd="/", exit_code=0, stdout=stdout, stderr="")


class ListWorktreesTest(unittest.TestCase):
    def test_should_parse_the_worktrees_of_a_repository(self):
        # Arrange
        stdout = (
            "worktree /srv/main\0HEAD abc123\0branch refs/heads/main\0\0"
            "worktree /srv/feature\0HEAD def456\0branch refs/heads/feature\0\0"
        )

        # Act
        worktrees = list_worktrees(lambda request: record_of(stdout), Path("/srv/main"))

        # Assert
        self.assertEqual(
            worktrees,
            (
                Worktree(path=Path("/srv/main"), head="abc123", branch="main"),
                Worktree(path=Path("/srv/feature"), head="def456", branch="feature"),
            ),
        )

    def test_should_skip_a_bare_repository(self):
        # Arrange
        stdout = "worktree /srv/main\0HEAD abc123\0bare\0\0"

        # Act
        worktrees = list_worktrees(lambda request: record_of(stdout), Path("/srv/main"))

        # Assert
        self.assertEqual(worktrees, ())

    def test_should_parse_a_detached_worktree_without_a_branch(self):
        # Arrange
        stdout = "worktree /srv/detached\0HEAD abc123\0detached\0\0"

        # Act
        worktrees = list_worktrees(lambda request: record_of(stdout), Path("/srv/main"))

        # Assert
        self.assertEqual(worktrees, (Worktree(path=Path("/srv/detached"), head="abc123", branch=None),))
