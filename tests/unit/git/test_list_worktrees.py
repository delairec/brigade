import unittest
from pathlib import Path

from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.system.run_process import ProcessRecord

BARE_AND_LINKED = (
    "worktree /srv/shop.git\0bare\0\0worktree /srv/worktrees/b42\0HEAD 4f2a9c1\0branch refs/heads/feat/b42\0\0"
)
DETACHED_AND_LOCKED = (
    "worktree /srv/worktrees/review\0HEAD 4f2a9c1\0detached\0\0"
    "worktree /srv/worktrees/b43\0HEAD 9b0e7d2\0branch refs/heads/feat/b43\0locked kept for the audit\0\0"
)


def create_git(listing: str):
    def answer_git(request):
        return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout=listing, stderr="", duration_ms=0)

    return answer_git


class ListWorktreesOfABareRepositoryTest(unittest.TestCase):
    def test_should_leave_out_the_bare_repository(self):
        # Act
        worktrees = list_worktrees(create_git(BARE_AND_LINKED), Path("/srv/shop.git"))

        # Assert
        self.assertEqual(
            worktrees,
            (
                Worktree(
                    path=Path("/srv/worktrees/b42"), head="4f2a9c1", branch="feat/b42", detached=False, locked=False
                ),
            ),
        )


class ListWorktreesDetachedOrLockedTest(unittest.TestCase):
    def test_should_tell_a_detached_worktree_and_a_locked_one(self):
        # Act
        worktrees = list_worktrees(create_git(DETACHED_AND_LOCKED), Path("/srv/shop"))

        # Assert
        self.assertEqual(
            worktrees,
            (
                Worktree(path=Path("/srv/worktrees/review"), head="4f2a9c1", branch=None, detached=True, locked=False),
                Worktree(
                    path=Path("/srv/worktrees/b43"), head="9b0e7d2", branch="feat/b43", detached=False, locked=True
                ),
            ),
        )
