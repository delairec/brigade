import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.tick.actions import RemoveTaskWorktree
from brigade.tick.remove_task_worktree import remove_task_worktree
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers


class RemoveTaskWorktreeTest(unittest.TestCase):
    def test_should_remove_the_worktree_from_the_repository_of_the_project(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        paths = create_test_paths(root)
        runner = RecordingProcessRunner(create_registry_answers(paths.config_root, {"shop": {"PATH": "/srv/shop"}}))
        action = RemoveTaskWorktree(project="shop", task="B1", worktree="/srv/shop/.brigade/worktrees/B1")

        # Act
        remove_task_worktree(create_test_runtime(paths, run_process=runner), action)

        # Assert
        self.assertEqual(
            runner.commands[-1],
            ("/srv/shop", ("git", "worktree", "remove", "--force", "/srv/shop/.brigade/worktrees/B1")),
        )
