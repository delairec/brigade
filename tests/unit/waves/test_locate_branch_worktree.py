import unittest
from pathlib import Path

from brigade.waves.locate_branch_worktree import locate_branch_worktree

DEFAULT_WORKTREE_ROOT = None


class LocateBranchWorktreeTest(unittest.TestCase):
    def test_should_name_the_worktree_of_a_branch_after_the_branch_its_slashes_turned_into_hyphens(self):
        # Act
        worktree = locate_branch_worktree(Path("/srv/shop"), DEFAULT_WORKTREE_ROOT, "integration/shop_w9")

        # Assert
        self.assertEqual(worktree, Path("/srv/shop/.brigade/worktrees/integration-shop_w9"))

    def test_should_place_the_worktree_of_a_branch_under_the_root_the_configuration_sets(self):
        # Act
        worktree = locate_branch_worktree(Path("/srv/shop"), "/var/worktrees", "integration/tides")

        # Assert
        self.assertEqual(worktree, Path("/var/worktrees/integration-tides"))
