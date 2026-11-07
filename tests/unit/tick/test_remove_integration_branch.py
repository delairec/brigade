import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.tick.actions import RemoveIntegrationBranch
from brigade.tick.remove_integration_branch import remove_integration_branch
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.lock_observing_runner import LockObservingRunner
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

TIDES_WORKTREE = "/srv/shop/.brigade/worktrees/integration-tides"
WORKTREE_REMOVAL = ("git", "worktree", "remove", "--force", TIDES_WORKTREE)
BRANCH_DELETION = ("git", "branch", "--quiet", "-D", "integration/tides")
NO_WORKTREE = None


class RemoveIntegrationBranchTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.registry = create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}})

    def test_should_remove_the_worktree_then_the_local_branch_and_touch_no_branch_of_the_forge(self):
        # Arrange
        runner = RecordingProcessRunner(self.registry)
        action = RemoveIntegrationBranch(project="shop", branch="integration/tides", worktree=TIDES_WORKTREE)

        # Act
        remove_integration_branch(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.commands[-2:], [("/srv/shop", WORKTREE_REMOVAL), ("/srv/shop", BRANCH_DELETION)])

    def test_should_remove_the_local_branch_alone_when_no_worktree_stands(self):
        # Arrange
        runner = RecordingProcessRunner(self.registry)
        action = RemoveIntegrationBranch(project="shop", branch="integration/tides", worktree=NO_WORKTREE)

        # Act
        remove_integration_branch(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.commands[-1], ("/srv/shop", BRANCH_DELETION))
        self.assertNotIn(WORKTREE_REMOVAL, runner.list_argvs())

    def test_should_remove_the_worktree_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        runner = LockObservingRunner(
            RecordingProcessRunner(self.registry), self.paths.lock_directory / "worktrees-shop.lock", WORKTREE_REMOVAL
        )
        action = RemoveIntegrationBranch(project="shop", branch="integration/tides", worktree=TIDES_WORKTREE)

        # Act
        remove_integration_branch(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])

    def test_should_delete_the_local_branch_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        runner = LockObservingRunner(
            RecordingProcessRunner(self.registry), self.paths.lock_directory / "worktrees-shop.lock", BRANCH_DELETION
        )
        action = RemoveIntegrationBranch(project="shop", branch="integration/tides", worktree=NO_WORKTREE)

        # Act
        remove_integration_branch(create_test_runtime(self.paths, run_process=runner), action)

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])
