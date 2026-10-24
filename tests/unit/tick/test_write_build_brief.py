import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.tick.actions import LaunchTask
from brigade.tick.write_build_brief import write_build_brief


class WriteBuildBriefTest(unittest.TestCase):
    def test_should_write_the_brief_of_the_task_naming_its_worktree_and_branch(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = LaunchTask(project="shop", wave="shop_w1", branch="integration/shop_w1", task="B1")
        worktree = BranchWorktree(
            path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/shop_w1/B1", start="integration/shop_w1"
        )

        # Act
        path = write_build_brief(state_root, action, worktree)

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
