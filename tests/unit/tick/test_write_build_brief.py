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
        action = LaunchTask(request="R1", project="shop", milestone="M1", wave="w1", branch="integration/w1", task="B1")
        worktree = BranchWorktree(
            path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/w1/B1", start="integration/w1"
        )

        # Act
        path = write_build_brief(state_root, action, worktree)

        # Assert
        brief = path.read_text()
        self.assertEqual(
            (path, "/srv/shop/.brigade/worktrees/B1" in brief, "task/w1/B1" in brief, "$" in brief),
            (state_root / "briefs" / "R1-B1.md", True, True, False),
        )
