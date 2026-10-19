import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.system.read_configuration import Configuration
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import prepare_task_worktree
from tests.unit.create_test_runtime import create_test_paths, create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

ACTION = LaunchTask(request="R1", project="shop", milestone="M1", wave="w1", branch="integration/w1", task="B1")
WORKTREE = Path("/srv/shop/.brigade/worktrees/B1")


class PrepareTaskWorktreeTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def create_runner(self, setup: str) -> RecordingProcessRunner:
        return RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop", "SETUP": setup}}),
                ("git", "cat-file", "-p", "integration/w1:.gitignore"): ProcessAnswer(stdout=".brigade/worktrees/\n"),
                ("make", "deps"): ProcessAnswer(stdout="deps installed\n", stderr="1 warning\n"),
            }
        )


class PrepareTaskWorktreeSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_add_the_task_worktree_and_run_its_setup_logging_each_line(self):
        # Arrange
        runner = self.create_runner("make deps")

        # Act
        worktree = prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            (
                worktree,
                [argv for _, argv in runner.commands if argv[0] != "awawa"],
                (self.paths.setup_directory / "shop" / "B1.log").read_text(),
            ),
            (
                BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="integration/w1"),
                [
                    ("git", "cat-file", "-p", "integration/w1:.gitignore"),
                    ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", str(WORKTREE), "integration/w1"),
                    ("make", "deps"),
                    ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD"),
                ],
                "$ make deps\ndeps installed\n1 warning\n",
            ),
        )

    def test_should_leave_the_ignore_file_alone_under_a_configured_worktree_root(self):
        # Arrange
        runner = self.create_runner("make deps")

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(worktree_root="/var/worktrees"), ACTION
        )

        # Assert
        self.assertNotIn(("git", "cat-file", "-p", "integration/w1:.gitignore"), [argv for _, argv in runner.commands])


class PrepareTaskWorktreeFailedSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_remove_the_worktree_park_the_task_and_refuse(self):
        # Arrange
        runner = self.create_runner('make "deps')

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            (
                str(refusal.exception),
                [argv for _, argv in runner.commands][-2:],
                [entry.event for entry in read_ledger(self.paths.state_root).entries],
            ),
            (
                'the setup of @TASK.B1 failed: the line make "deps splits into no argv: No closing quotation',
                [
                    ("git", "worktree", "remove", "--force", str(WORKTREE)),
                    ("git", "branch", "--quiet", "-D", "task/w1/B1"),
                ],
                [TaskState(wave="w1", task="B1", state="parked")],
            ),
        )
