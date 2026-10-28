import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree, prepare_task_worktree
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
TASK_BRANCH_DESCENDS = ("git", "merge-base", "--is-ancestor", "integration/w1", "task/w1/B1")
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


def read_no_environment(key: str) -> dict:
    return {}


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
        forge: tuple = (),
        answers: dict | None = None,
    ) -> RecordingProcessRunner:
        root = str(self.paths.config_root)
        fields = [{"name": "PATH", "atoms": ['"/srv/shop"']}, *forge, *setup]
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
                **(answers or {}),
            }
        )


class PrepareTaskWorktreeSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_add_the_task_worktree_and_run_its_setup_logging_each_line(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(prepared.worktree, BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="integration/w1"))
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
            create_test_runtime(self.paths, run_process=runner),
            Configuration(worktree_root="/var/worktrees"),
            ACTION,
            read_no_environment,
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
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(prepared.worktree, BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="integration/w1"))
        self.assertEqual(
            runner.commands[-4:],
            [
                ("/srv/shop", LIST_WORKTREES),
                (str(WORKTREE), TASK_BRANCH_DESCENDS),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )

    def test_should_add_a_worktree_on_the_existing_branch_of_the_task(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(
            runner.commands[-5:-3],
            [
                ("/srv/shop", FIND_TASK_BRANCH),
                ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "task/w1/B1")),
            ],
        )

    def test_should_not_take_a_worktree_of_the_branch_outside_the_worktree_root_for_the_task_worktree(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_BRANCH_LISTED_ELSEWHERE, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(
            runner.commands[-4],
            ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "task/w1/B1")),
        )


class PrepareTaskWorktreeFailedSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_park_the_task_and_refuse(self):
        # Arrange
        runner = self.create_runner(UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

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
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

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
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

        # Assert
        self.assertEqual(str(refusal.exception), "the setup of @TASK.B1 failed: false exited 1: ")

    def test_should_run_no_line_after_the_failing_one(self):
        # Arrange
        runner = self.create_runner(FAILING_SETUP, MAKE_DEPS)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

        # Assert
        self.assertEqual(
            runner.commands,
            [
                (str(self.paths.config_root), ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root))),
                (
                    str(self.paths.config_root),
                    ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ),
                ("/srv/shop", ("git", "cat-file", "-p", "integration/w1:.gitignore")),
                ("/srv/shop", ("git", "worktree", "list", "--porcelain", "-z")),
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/task/w1/B1")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "task/w1/B1",
                        "/srv/shop/.brigade/worktrees/B1",
                        "integration/w1",
                    ),
                ),
                ("/srv/shop/.brigade/worktrees/B1", ("false",)),
            ],
        )

    def test_should_run_no_line_of_a_setup_holding_a_line_that_splits_into_no_argv(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

        # Assert
        self.assertEqual(
            runner.commands,
            [
                (str(self.paths.config_root), ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root))),
                (
                    str(self.paths.config_root),
                    ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ),
                ("/srv/shop", ("git", "cat-file", "-p", "integration/w1:.gitignore")),
                ("/srv/shop", ("git", "worktree", "list", "--porcelain", "-z")),
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/task/w1/B1")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "task/w1/B1",
                        "/srv/shop/.brigade/worktrees/B1",
                        "integration/w1",
                    ),
                ),
            ],
        )

    def test_should_refuse_a_setup_leaving_the_head_off_the_wave_branch(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, ancestry=HEAD_OFF_THE_WAVE_BRANCH)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
            )

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
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(
            runner.commands,
            [
                (str(self.paths.config_root), ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root))),
                (
                    str(self.paths.config_root),
                    ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ),
                ("/srv/shop", ("git", "cat-file", "-p", "integration/w1:.gitignore")),
                ("/srv/shop", ("git", "worktree", "list", "--porcelain", "-z")),
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/task/w1/B1")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "task/w1/B1",
                        "/srv/shop/.brigade/worktrees/B1",
                        "integration/w1",
                    ),
                ),
                ("/srv/shop/.brigade/worktrees/B1", ("touch", "$PWD")),
                ("/srv/shop/.brigade/worktrees/B1", ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )


class PrepareTaskWorktreeUnderTheLockTest(PrepareTaskWorktreeTestCase):
    def test_should_add_the_worktree_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        lock = self.paths.lock_directory / "worktrees-shop.lock"
        runner = LockObservingRunner(self.create_runner(MAKE_DEPS), lock, ADD_TASK_WORKTREE)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])


ON_GITHUB = ({"name": "FORGE", "atoms": ['"github"']},)
CLI_ENVIRONMENT = {"GH_TOKEN": "token-of-the-bot"}
FETCH_THE_WAVE_BRANCH = ("git", "fetch", "--quiet", "origin", "integration/w1")
OFF_THE_WAVE_BRANCH = {TASK_BRANCH_DESCENDS: ProcessAnswer(exit_code=1)}
REBASE_ON_THE_WAVE_BRANCH = ("git", "rebase", "integration/w1")
STOPPED_ON_A_CONFLICT = {
    TASK_BRANCH_DESCENDS: ProcessAnswer(exit_code=1),
    REBASE_ON_THE_WAVE_BRANCH: ProcessAnswer(exit_code=1),
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="5c1d2e0\n"),
}


def read_cli_environment(key: str) -> dict:
    return {"cli": CLI_ENVIRONMENT}[key]


class PrepareTaskWorktreeOnGithubTest(PrepareTaskWorktreeTestCase):
    def test_should_cut_the_task_branch_from_the_wave_branch_of_the_forge_and_check_the_setup_against_it(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, forge=ON_GITHUB)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_cli_environment
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="task/w1/B1", start="origin/integration/w1"),
                conflicted=False,
            ),
        )
        self.assertEqual(
            runner.commands[-4:],
            [
                ("/srv/shop", FIND_TASK_BRANCH),
                (
                    "/srv/shop",
                    ("git", "worktree", "add", "--quiet", "-b", "task/w1/B1", str(WORKTREE), "origin/integration/w1"),
                ),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), ("git", "merge-base", "--is-ancestor", "origin/integration/w1", "HEAD")),
            ],
        )

    def test_should_fetch_the_wave_branch_with_the_environment_of_the_cli_slot(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, forge=ON_GITHUB)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_cli_environment
        )

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=FETCH_THE_WAVE_BRANCH, cwd="/srv/shop", timeout_s=REMOTE_TIMEOUT_S, environment=CLI_ENVIRONMENT
            ),
            runner.requests,
        )

    def test_should_rebase_an_existing_branch_onto_the_wave_branch_of_the_forge(self):
        # Arrange
        runner = self.create_runner(
            MAKE_DEPS,
            forge=ON_GITHUB,
            branch=TASK_BRANCH_FOUND,
            answers={
                ("git", "merge-base", "--is-ancestor", "origin/integration/w1", "task/w1/B1"): ProcessAnswer(
                    exit_code=1
                )
            },
        )

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_cli_environment
        )

        # Assert
        self.assertIn((str(WORKTREE), ("git", "rebase", "origin/integration/w1")), runner.commands)


class PrepareTaskWorktreeOfABranchOffTheWaveBranchTest(PrepareTaskWorktreeTestCase):
    def test_should_rebase_the_branch_onto_the_wave_branch_before_the_setup(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertFalse(prepared.conflicted)
        self.assertEqual(
            runner.commands[-4:],
            [
                (str(WORKTREE), TASK_BRANCH_DESCENDS),
                (str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), REQUIRE_THE_WAVE_BRANCH),
            ],
        )

    def test_should_leave_a_branch_descending_from_the_wave_branch_unrebased(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_WORKTREE_LISTED, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertNotIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)

    def test_should_abort_a_rebase_stopped_on_a_conflict_and_run_no_setup(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=STOPPED_ON_A_CONFLICT)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, read_no_environment
        )

        # Assert
        self.assertTrue(prepared.conflicted)
        self.assertEqual(runner.commands[-1], (str(WORKTREE), ("git", "rebase", "--abort")))
