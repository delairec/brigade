import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree
from brigade.tick.write_build_brief import write_build_brief


class WriteBuildBriefTest(unittest.TestCase):
    def test_should_write_the_brief_of_the_task_naming_its_worktree_and_branch(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = LaunchTask(
            project="shop", wave="shop_w1", branch="integration/shop_w1", task="B1", checks_passed=False
        )
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/shop_w1/B1", start="integration/shop_w1"
            ),
            conflicted=False,
            on_start=True,
        )

        # Act
        path = write_build_brief(state_root, action, prepared)

        # Assert
        self.assertEqual(path, state_root / "briefs" / "shop_w1-B1.md")
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch task/shop_w1/B1,"
            " cut from the head of integration/shop_w1.\n",
        )

    def test_should_tell_the_build_of_a_branch_left_off_its_start_that_the_tick_rebases_it_once_its_checks_pass(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = LaunchTask(
            project="shop", wave="shop_w1", branch="integration/shop_w1", task="B1", checks_passed=False
        )
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/shop_w1/B1", start="integration/shop_w1"
            ),
            conflicted=False,
            on_start=False,
        )

        # Act
        path = write_build_brief(state_root, action, prepared)

        # Assert
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch task/shop_w1/B1,"
            " left as it stands, off the head of integration/shop_w1: do not rebase it; the tick rebases it"
            " onto integration/shop_w1 once the checks of its pull request pass.\n",
        )
