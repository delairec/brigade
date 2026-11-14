import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.tick.actions import RemoveLeftover
from brigade.tick.remove_leftover import remove_leftover
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.lock_observing_runner import LockObservingRunner
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

SPROUT_WORKTREE = "/srv/shop/.brigade/worktrees/S7"
WORKTREE_REMOVAL = ("git", "worktree", "remove", "--force", SPROUT_WORKTREE)
BRANCH_DELETION = ("git", "branch", "--quiet", "-D", "feature/S7-sprout")
NO_WORKTREE = None
NO_BRANCH = None


class RemoveLeftoverTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.registry = create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}})

    def test_should_remove_the_worktree_then_the_stale_branch(self):
        # Arrange
        runner = RecordingProcessRunner(self.registry)
        action = RemoveLeftover(project="shop", branch="feature/S7-sprout", worktree=SPROUT_WORKTREE)

        # Act
        remove_leftover(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.commands[-2:], [("/srv/shop", WORKTREE_REMOVAL), ("/srv/shop", BRANCH_DELETION)])

    def test_should_delete_the_stale_branch_alone_when_it_has_no_worktree(self):
        # Arrange
        runner = RecordingProcessRunner(self.registry)
        action = RemoveLeftover(project="shop", branch="feature/S7-sprout", worktree=NO_WORKTREE)

        # Act
        remove_leftover(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.commands[-1], ("/srv/shop", BRANCH_DELETION))
        self.assertNotIn(WORKTREE_REMOVAL, runner.list_argvs())

    def test_should_remove_the_stale_worktree_alone_when_it_holds_no_branch(self):
        # Arrange
        runner = RecordingProcessRunner(self.registry)
        action = RemoveLeftover(project="shop", branch=NO_BRANCH, worktree=SPROUT_WORKTREE)

        # Act
        remove_leftover(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.commands[-1], ("/srv/shop", WORKTREE_REMOVAL))
        self.assertNotIn(BRANCH_DELETION, runner.list_argvs())

    def test_should_remove_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        runner = LockObservingRunner(
            RecordingProcessRunner(self.registry), self.paths.lock_directory / "worktrees-shop.lock", BRANCH_DELETION
        )
        action = RemoveLeftover(project="shop", branch="feature/S7-sprout", worktree=NO_WORKTREE)

        # Act
        remove_leftover(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])
