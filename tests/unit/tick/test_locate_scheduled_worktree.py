import unittest
from pathlib import Path

from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree


class LocateScheduledWorktreeTest(unittest.TestCase):
    def test_should_place_the_worktree_under_the_root_the_configuration_sets(self):
        for worktree_root, expected in [
            (None, Path("/srv/shop/.brigade/worktrees/B1")),
            ("../shop-worktrees", Path("/srv/shop/../shop-worktrees/B1")),
            ("/var/worktrees", Path("/var/worktrees/B1")),
        ]:
            with self.subTest(worktree_root=worktree_root):
                # Act
                worktree = locate_scheduled_worktree(Path("/srv/shop"), worktree_root, "B1")

                # Assert
                self.assertEqual(worktree, expected)
