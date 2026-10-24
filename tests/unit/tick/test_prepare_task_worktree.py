import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.system.parse_configuration import Configuration
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import prepare_task_worktree
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.lock_observing_runner import LockObservingRunner
from tests.unit.recording_process_runner import SILENT_SUCCESS, ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

ACTION = LaunchTask(project="shop", wave="w1", branch="integration/w1", task="B1")
WORKTREE = Path("/srv/shop/.brigade/worktrees/B1")
ADD_TASK_WORKTREE = ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", str(WORKTREE), "integration/w1")
REQUIRE_THE_WAVE_BRANCH = ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")
HEAD_OFF_THE_WAVE_BRANCH = ProcessAnswer(exit_code=1)
LIST_WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
FIND_TASK_BRANCH = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/task/w1/B1")
NO_TASK_BRANCH = ProcessAnswer(exit_code=1)
TASK_BRANCH_FOUND = ProcessAnswer(stdout="5c1d2e0\n")
MAIN_CHECKOUT_ALONE = ProcessAnswer(stdout="worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0")
TASK_BRANCH_LISTED_ELSEWHERE = ProcessAnswer(
    stdout=(
        "worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0"
        "worktree /var/old/B1\0HEAD 5c1d2e0\0branch refs/heads/task/w1/B1\0\0"
    )
)
TASK_WORKTREE_LISTED = ProcessAnswer(
    stdout=(
        "worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0"
        "worktree /srv/shop/.brigade/worktrees/B1\0HEAD 5c1d2e0\0branch refs/heads/task/w1/B1\0\0"
    )
)


MAKE_DEPS = {"name": "SETUP", "atoms": ['"make deps"']}
UNCLOSED_QUOTE = {"name": "SETUP", "atoms": ['"make \\"deps"']}
FAILING_SETUP = {"name": "SETUP", "atoms": ['"false"']}
TOUCH_THE_WORKTREE = {"name": "SETUP", "atoms": ['"touch \\"$PWD\\""']}


class PrepareTaskWorktreeTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def create_runner(
        self,
        *setup: dict,
        worktrees: ProcessAnswer = MAIN_CHECKOUT_ALONE,
        branch: ProcessAnswer = NO_TASK_BRANCH,
        ancestry: ProcessAnswer = SILENT_SUCCESS,
    ) -> RecordingProcessRunner:
        root = str(self.paths.config_root)
        fields = [{"name": "PATH", "atoms": ['"/srv/shop"']}, *setup]
        return RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {}}),
                ("awawa", "show", "@PROJECT.shop", "--json", root): ProcessAnswer(
                    stdout=json.dumps({"fields": fields})
                ),
                ("git", "cat-file", "-p", "integration/w1:.gitignore"): ProcessAnswer(stdout=".brigade/worktrees/\n"),
                LIST_WORKTREES: worktrees,
                FIND_TASK_BRANCH: branch,
                ("make", "deps"): ProcessAnswer(stdout="deps installed\n", stderr="1 warning\n"),
                ("false",): ProcessAnswer(exit_code=1),
                REQUIRE_THE_WAVE_BRANCH: ancestry,
            }
        )


class PrepareTaskWorktreeSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_add_the_task_worktree_and_run_its_setup_logging_each_line(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS)

        # Act
        worktree = prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(worktree, BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="integration/w1"))
        self.assertEqual(
            runner.commands[-6:],
            [
                ("/srv/shop", ("git", "cat-file", "-p", "integration/w1:.gitignore")),
                ("/srv/shop", LIST_WORKTREES),
                ("/srv/shop", FIND_TASK_BRANCH),
                (
                    "/srv/shop",
                    ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", str(WORKTREE), "integration/w1"),
                ),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )
        self.assertEqual(
            (self.paths.setup_directory / "shop" / "B1.log").read_text(), "$ make deps\ndeps installed\n1 warning\n"
        )

    def test_should_leave_the_ignore_file_alone_under_a_configured_worktree_root(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(worktree_root="/var/worktrees"), ACTION
        )

        # Assert
        self.assertEqual(
            runner.commands[-6:],
            [
                (
                    str(self.paths.config_root),
                    ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ),
                ("/srv/shop", LIST_WORKTREES),
                ("/srv/shop", FIND_TASK_BRANCH),
                (
                    "/srv/shop",
                    ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", "/var/worktrees/B1", "integration/w1"),
                ),
                ("/var/worktrees/B1", ("make", "deps")),
                ("/var/worktrees/B1", ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )


class PrepareTaskWorktreeOfAQueuedAgainTaskTest(PrepareTaskWorktreeTestCase):
    def test_should_reuse_the_worktree_of_the_task_and_run_its_setup_again(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_WORKTREE_LISTED, branch=TASK_BRANCH_FOUND)

        # Act
        worktree = prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(worktree, BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="integration/w1"))
        self.assertEqual(
            runner.commands[-3:],
            [
                ("/srv/shop", LIST_WORKTREES),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )

    def test_should_add_a_worktree_on_the_existing_branch_of_the_task(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            runner.commands[-4:-2],
            [
                ("/srv/shop", FIND_TASK_BRANCH),
                ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "task/w1/B1")),
            ],
        )

    def test_should_not_take_a_worktree_of_the_branch_outside_the_worktree_root_for_the_task_worktree(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_BRANCH_LISTED_ELSEWHERE, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            runner.commands[-3],
            ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "task/w1/B1")),
        )


class PrepareTaskWorktreeFailedSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_park_the_task_and_refuse(self):
        # Arrange
        runner = self.create_runner(UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            'the setup of @TASK.B1 failed: the line make "deps splits into no argv: No closing quotation',
        )
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[0].event,
            TaskState(wave="w1", task="B1", state="parked", reason="setup failed"),
        )

    def test_should_leave_the_worktree_and_the_branch_of_the_task_in_place(self):
        # Arrange
        runner = self.create_runner(UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            runner.commands[-1],
            (
                "/srv/shop",
                ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", str(WORKTREE), "integration/w1"),
            ),
        )

    def test_should_name_the_setup_line_exiting_non_zero(self):
        # Arrange
        runner = self.create_runner(FAILING_SETUP)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(str(refusal.exception), "the setup of @TASK.B1 failed: false exited 1: ")

    def test_should_run_no_line_after_the_failing_one(self):
        # Arrange
        runner = self.create_runner(FAILING_SETUP, MAKE_DEPS)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(runner.commands[-1], (str(WORKTREE), ("false",)))

    def test_should_run_no_line_of_a_setup_holding_a_line_that_splits_into_no_argv(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(runner.commands[-1], ("/srv/shop", ADD_TASK_WORKTREE))

    def test_should_refuse_a_setup_leaving_the_head_off_the_wave_branch(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, ancestry=HEAD_OFF_THE_WAVE_BRANCH)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the setup of @TASK.B1 failed: git merge-base --is-ancestor integration/w1 HEAD exited 1: ",
        )


class PrepareTaskWorktreeOfASetupLineInShellSyntaxTest(PrepareTaskWorktreeTestCase):
    def test_should_run_the_line_as_one_argv_without_a_shell(self):
        # Arrange
        runner = self.create_runner(TOUCH_THE_WORKTREE)

        # Act
        prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(runner.commands[-2], (str(WORKTREE), ("touch", "$PWD")))


class PrepareTaskWorktreeUnderTheLockTest(PrepareTaskWorktreeTestCase):
    def test_should_add_the_worktree_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        lock = self.paths.lock_directory / "worktrees-shop.lock"
        runner = LockObservingRunner(self.create_runner(MAKE_DEPS), lock, ADD_TASK_WORKTREE)

        # Act
        prepare_task_worktree(create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION)

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])
