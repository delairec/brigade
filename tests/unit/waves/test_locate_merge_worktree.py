import unittest
from pathlib import Path

from brigade.waves.locate_merge_worktree import MergeWorktree, locate_merge_worktree
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

REPOSITORY = Path("/srv/tidepool")
NO_CONFIGURED_ROOT = None
BRANCH = "integration/tides"


def create_git(worktree_list: str) -> ScriptedProcessRunner:
    return ScriptedProcessRunner({("git", "worktree", "list"): ProcessAnswer(stdout=worktree_list)})


class LocateMergeWorktreeTest(unittest.TestCase):
    def test_should_locate_where_the_tick_opens_it_when_no_worktree_holds_the_branch(self):
        # Arrange
        git = create_git("worktree /srv/tidepool\0HEAD 8885daa\0branch refs/heads/main\0\0")

        # Act
        located = locate_merge_worktree(git.run, REPOSITORY, NO_CONFIGURED_ROOT, BRANCH)

        # Assert
        self.assertEqual(
            located, MergeWorktree(path=Path("/srv/tidepool/.brigade/worktrees/integration-tides"), opened=False)
        )

    def test_should_locate_the_worktree_holding_the_branch_wherever_it_is(self):
        # Arrange
        git = create_git(
            "worktree /srv/tidepool\0HEAD 8885daa\0branch refs/heads/main\0\0"
            "worktree /srv/elsewhere\0HEAD 8885daa\0branch refs/heads/integration/tides\0\0"
        )

        # Act
        located = locate_merge_worktree(git.run, REPOSITORY, NO_CONFIGURED_ROOT, BRANCH)

        # Assert
        self.assertEqual(located, MergeWorktree(path=Path("/srv/elsewhere"), opened=True))
