import unittest
from pathlib import Path

from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.system.run_process import ProcessRecord

BARE_AND_LINKED = (
    "worktree /srv/shop.git\0bare\0\0worktree /srv/worktrees/b42\0HEAD 4f2a9c1\0branch refs/heads/feat/b42\0\0"
)


def answer_git(request):
    return ProcessRecord(
        argv=request.argv, cwd=request.cwd, exit_code=0, stdout=BARE_AND_LINKED, stderr="", duration_ms=0
    )


class ListWorktreesOfABareRepositoryTest(unittest.TestCase):
    def test_should_leave_out_the_bare_repository(self):
        # Act
        worktrees = list_worktrees(answer_git, Path("/srv/shop.git"))

        # Assert
        self.assertEqual(worktrees, (Worktree(path=Path("/srv/worktrees/b42"), head="4f2a9c1", branch="feat/b42"),))
