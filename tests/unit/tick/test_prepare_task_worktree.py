import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_started import WaveStarted
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.tick.actions import LaunchTask
from brigade.tick.head_proof import ForgeCheck, HeadChecks, HeadProof, HoldingHead
from brigade.tick.prepare_task_worktree import PreparedWorktree, prepare_task_worktree
from brigade.tick.tick_forge import TickForge
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.lock_observing_runner import LockObservingRunner
from tests.unit.recording_process_runner import SILENT_SUCCESS, ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

ACTION = LaunchTask(
    project="shop",
    wave="w1",
    branch="integration/w1",
    task="B1",
    task_branch="feature/B1-task",
    pull_request_checks=None,
)
TASK_HEAD = "5c1d2e0"
WAVE_HEAD = "9a8b7c6"
ACTION_WITH_PASSED_PULL_REQUEST_CHECKS = LaunchTask(
    project="shop",
    wave="w1",
    branch="integration/w1",
    task="B1",
    task_branch="feature/B1-task",
    pull_request_checks=HeadChecks(head=TASK_HEAD, checks=(ForgeCheck(name="unit", verdict="success"),)),
)
ACTION_WITH_PENDING_PULL_REQUEST_CHECKS = LaunchTask(
    project="shop",
    wave="w1",
    branch="integration/w1",
    task="B1",
    task_branch="feature/B1-task",
    pull_request_checks=HeadChecks(head=TASK_HEAD, checks=(ForgeCheck(name="unit", verdict="pending"),)),
)
ACTION_WITH_PULL_REQUEST_CHECKS_OF_AN_OLDER_HEAD = LaunchTask(
    project="shop",
    wave="w1",
    branch="integration/w1",
    task="B1",
    task_branch="feature/B1-task",
    pull_request_checks=HeadChecks(head="0ld4ead", checks=(ForgeCheck(name="unit", verdict="success"),)),
)
WORKTREE = Path("/srv/shop/.brigade/worktrees/B1")
ADD_TASK_WORKTREE = ("git", "worktree", "add", "--quiet", "-b", "feature/B1-task", str(WORKTREE), "integration/w1")
REQUIRE_THE_WAVE_BRANCH = ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")
HEAD_OFF_THE_WAVE_BRANCH = ProcessAnswer(exit_code=1)
TASK_BRANCH_DESCENDS = ("git", "merge-base", "--is-ancestor", "integration/w1", "feature/B1-task")
LIST_WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
FIND_TASK_BRANCH = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feature/B1-task")
NO_TASK_BRANCH = ProcessAnswer(exit_code=1)
TASK_BRANCH_FOUND = ProcessAnswer(stdout="5c1d2e0\n")
MAIN_CHECKOUT_ALONE = ProcessAnswer(stdout="worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0")
TASK_BRANCH_LISTED_ELSEWHERE = ProcessAnswer(
    stdout=(
        "worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0"
        "worktree /var/old/B1\0HEAD 5c1d2e0\0branch refs/heads/feature/B1-task\0\0"
    )
)
TASK_WORKTREE_LISTED = ProcessAnswer(
    stdout=(
        "worktree /srv/shop\0HEAD 8885daa\0branch refs/heads/main\0\0"
        "worktree /srv/shop/.brigade/worktrees/B1\0HEAD 5c1d2e0\0branch refs/heads/feature/B1-task\0\0"
    )
)


def read_no_environment(key: str) -> dict:
    return {}


MAKE_DEPS = {"name": "SETUP", "atoms": ['"make deps"']}
UNCLOSED_QUOTE = {"name": "SETUP", "atoms": ['"make \\"deps"']}
FAILING_SETUP = {"name": "SETUP", "atoms": ['"false"']}
TOUCH_THE_WORKTREE = {"name": "SETUP", "atoms": ['"touch \\"$PWD\\""']}


def list_no_check_run(repository: str, branch: str) -> list[dict]:
    return []


NO_FORGE = TickForge(read_environment=read_no_environment, list_check_runs=list_no_check_run)


class CheckRunsListingDouble:
    def __init__(self, check_runs: list[dict]):
        self.check_runs = check_runs

    def list_check_runs(self, repository: str, branch: str) -> list[dict]:
        return self.check_runs


def create_wave_head_check_run(conclusion: str) -> dict:
    return {
        "pull_request": None,
        "branch": "integration/w1",
        "head": WAVE_HEAD,
        "name": "unit",
        "conclusion": conclusion,
        "link": "https://github.com/delairec/shop/actions/runs/1/job/2",
    }


class PrepareTaskWorktreeTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def record_commit_checks(self, commit: str, exit_code: int) -> None:
        record = self.paths.state_root / "commit-checks" / "shop" / f"{commit}.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": "shop",
                    "commit": commit,
                    "checks": [{"command": "make test", "exit_code": exit_code}],
                }
            ),
            encoding="utf-8",
        )

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
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared.worktree, BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1")
        )
        self.assertEqual(
            runner.commands[-6:],
            [
                ("/srv/shop", ("git", "cat-file", "-p", "integration/w1:.gitignore")),
                ("/srv/shop", LIST_WORKTREES),
                ("/srv/shop", FIND_TASK_BRANCH),
                (
                    "/srv/shop",
                    ("git", "worktree", "add", "--quiet", "-b", "feature/B1-task", str(WORKTREE), "integration/w1"),
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
            NO_FORGE,
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
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "feature/B1-task",
                        "/var/worktrees/B1",
                        "integration/w1",
                    ),
                ),
                ("/var/worktrees/B1", ("make", "deps")),
                ("/var/worktrees/B1", ("git", "merge-base", "--is-ancestor", "integration/w1", "HEAD")),
            ],
        )

    def test_should_cut_a_task_naming_no_milestone_from_main_without_committing_on_it(self):
        # Arrange
        runner = self.create_runner(
            {"name": "MAIN", "atoms": ['"main"']},
            answers={
                ("git", "cat-file", "-p", "main:.gitignore"): ProcessAnswer(stdout="*.pyc\n"),
                ("git", "merge-base", "--is-ancestor", "main", "HEAD"): SILENT_SUCCESS,
            },
        )
        action = LaunchTask(
            project="shop", wave="w1", branch="main", task="B1", task_branch="feature/B1-task", pull_request_checks=None
        )

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), action, NO_FORGE
        )

        # Assert
        self.assertEqual(prepared.worktree, BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="main"))
        self.assertEqual(
            runner.commands[-5:],
            [
                (
                    str(self.paths.config_root),
                    ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ),
                ("/srv/shop", LIST_WORKTREES),
                ("/srv/shop", FIND_TASK_BRANCH),
                ("/srv/shop", ("git", "worktree", "add", "--quiet", "-b", "feature/B1-task", str(WORKTREE), "main")),
                (str(WORKTREE), ("git", "merge-base", "--is-ancestor", "main", "HEAD")),
            ],
        )


class PrepareTaskWorktreeOfAQueuedAgainTaskTest(PrepareTaskWorktreeTestCase):
    def test_should_reuse_the_worktree_of_the_task_and_run_its_setup_again(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_WORKTREE_LISTED, branch=TASK_BRANCH_FOUND)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared.worktree, BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1")
        )
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
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            runner.commands[-5:-3],
            [
                ("/srv/shop", FIND_TASK_BRANCH),
                ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "feature/B1-task")),
            ],
        )

    def test_should_not_take_a_worktree_of_the_branch_outside_the_worktree_root_for_the_task_worktree(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_BRANCH_LISTED_ELSEWHERE, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            runner.commands[-4],
            ("/srv/shop", ("git", "worktree", "add", "--quiet", str(WORKTREE), "feature/B1-task")),
        )


class PrepareTaskWorktreeFailedSetUpTest(PrepareTaskWorktreeTestCase):
    def test_should_park_the_task_and_refuse(self):
        # Arrange
        runner = self.create_runner(UNCLOSED_QUOTE)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
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
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
            )

        # Assert
        self.assertEqual(
            runner.commands[-1],
            (
                "/srv/shop",
                ("git", "worktree", "add", "--quiet", "-b", "feature/B1-task", str(WORKTREE), "integration/w1"),
            ),
        )

    def test_should_name_the_setup_line_exiting_non_zero(self):
        # Arrange
        runner = self.create_runner(FAILING_SETUP)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
            )

        # Assert
        self.assertEqual(str(refusal.exception), "the setup of @TASK.B1 failed: false exited 1: ")

    def test_should_run_no_line_after_the_failing_one(self):
        # Arrange
        runner = self.create_runner(FAILING_SETUP, MAKE_DEPS)

        # Act
        with self.assertRaises(BrigadeError):
            prepare_task_worktree(
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
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
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feature/B1-task")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "feature/B1-task",
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
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
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
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feature/B1-task")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "feature/B1-task",
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
                create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
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
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
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
                ("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feature/B1-task")),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "feature/B1-task",
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
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(runner.lock_free_at_the_command, [False])


ON_GITHUB = ({"name": "FORGE", "atoms": ['"github"']},)
CLI_ENVIRONMENT = {"GH_TOKEN": "token-of-the-bot"}
FETCH_THE_WAVE_BRANCH = ("git", "fetch", "--quiet", "origin", "integration/w1")
READ_THE_TASK_HEAD = ("git", "rev-parse", "HEAD")
READ_THE_WAVE_HEAD = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "integration/w1^{commit}")
OFF_THE_WAVE_BRANCH = {
    TASK_BRANCH_DESCENDS: ProcessAnswer(exit_code=1),
    READ_THE_TASK_HEAD: ProcessAnswer(stdout=f"{TASK_HEAD}\n"),
    READ_THE_WAVE_HEAD: ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
}
ADD_A_CHECKOUT_OF_THE_TASK_HEAD = ("git", "worktree", "add", "--quiet", "--detach")
REBASE_ON_THE_WAVE_BRANCH = ("git", "rebase", "--fork-point", "integration/w1")
STOPPED_ON_A_CONFLICT = {
    TASK_BRANCH_DESCENDS: ProcessAnswer(exit_code=1),
    REBASE_ON_THE_WAVE_BRANCH: ProcessAnswer(exit_code=1),
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="5c1d2e0\n"),
}


def read_cli_environment(key: str) -> dict:
    return {"cli": CLI_ENVIRONMENT}[key]


CLI_FORGE = TickForge(read_environment=read_cli_environment, list_check_runs=list_no_check_run)


class PrepareTaskWorktreeOnGithubTest(PrepareTaskWorktreeTestCase):
    def test_should_cut_the_task_branch_from_the_wave_branch_of_the_forge_and_check_the_setup_against_it(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, forge=ON_GITHUB)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, CLI_FORGE
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="origin/integration/w1"),
                conflicted=False,
                on_start=True,
            ),
        )
        self.assertEqual(
            runner.commands[-4:],
            [
                ("/srv/shop", FIND_TASK_BRANCH),
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        "feature/B1-task",
                        str(WORKTREE),
                        "origin/integration/w1",
                    ),
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
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, CLI_FORGE
        )

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=FETCH_THE_WAVE_BRANCH, cwd="/srv/shop", timeout_s=REMOTE_TIMEOUT_S, environment=CLI_ENVIRONMENT
            ),
            runner.requests,
        )

    def create_runner_of_a_branch_off_the_wave_branch_of_the_forge(self) -> RecordingProcessRunner:
        return self.create_runner(
            MAKE_DEPS,
            forge=ON_GITHUB,
            branch=TASK_BRANCH_FOUND,
            answers={
                ("git", "merge-base", "--is-ancestor", "origin/integration/w1", "feature/B1-task"): ProcessAnswer(
                    exit_code=1
                ),
                READ_THE_TASK_HEAD: ProcessAnswer(stdout=f"{TASK_HEAD}\n"),
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "--end-of-options",
                    "origin/integration/w1^{commit}",
                ): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
            },
        )

    def test_should_rebase_an_existing_green_branch_onto_the_green_wave_branch_of_the_forge(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner_of_a_branch_off_the_wave_branch_of_the_forge()
        forge = TickForge(read_environment=read_cli_environment, list_check_runs=list_no_check_run)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, forge
        )

        # Assert
        self.assertIn((str(WORKTREE), ("git", "rebase", "--fork-point", "origin/integration/w1")), runner.commands)

    def test_should_prove_the_wave_branch_green_by_the_check_runs_of_the_forge_on_its_head(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        runner = self.create_runner_of_a_branch_off_the_wave_branch_of_the_forge()
        listing = CheckRunsListingDouble([create_wave_head_check_run("success")])
        forge = TickForge(read_environment=read_cli_environment, list_check_runs=listing.list_check_runs)
        checkout_of_the_wave_head = str(self.paths.state_root / "head-checks" / "shop" / WAVE_HEAD)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, forge
        )

        # Assert
        self.assertNotIn(
            ("/srv/shop", (*ADD_A_CHECKOUT_OF_THE_TASK_HEAD, checkout_of_the_wave_head, WAVE_HEAD)), runner.commands
        )

    def test_should_hold_a_branch_off_a_wave_branch_whose_check_run_of_the_forge_failed_on_its_head(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        runner = self.create_runner_of_a_branch_off_the_wave_branch_of_the_forge()
        listing = CheckRunsListingDouble([create_wave_head_check_run("failure")])
        forge = TickForge(read_environment=read_cli_environment, list_check_runs=listing.list_check_runs)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, forge
        )

        # Assert
        self.assertEqual(
            prepared.held_by,
            HoldingHead(
                branch="integration/w1", proof=HeadProof(commit=WAVE_HEAD, state="red", failed_commands=("unit",))
            ),
        )


class PrepareTaskWorktreeOfABranchOffTheWaveBranchTest(PrepareTaskWorktreeTestCase):
    def test_should_rebase_a_green_branch_onto_the_green_wave_branch_before_the_setup_and_require_it(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertFalse(prepared.conflicted)
        self.assertEqual(
            runner.commands[-3:],
            [
                (str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), REQUIRE_THE_WAVE_BRANCH),
            ],
        )

    def test_should_hand_over_a_rebased_branch_as_put_on_the_head_of_the_wave_branch(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1"),
                conflicted=False,
                on_start=True,
                rebased=True,
                failed_commands=(),
            ),
        )

    def test_should_prove_the_branch_green_by_the_check_runs_its_pull_request_passed_at_its_head(self):
        # Arrange
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner),
            Configuration(),
            ACTION_WITH_PASSED_PULL_REQUEST_CHECKS,
            NO_FORGE,
        )

        # Assert
        self.assertIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)

    def test_should_check_the_branch_on_a_checkout_of_its_head_when_its_pull_request_was_checked_at_another(self):
        # Arrange
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner),
            Configuration(),
            ACTION_WITH_PULL_REQUEST_CHECKS_OF_AN_OLDER_HEAD,
            NO_FORGE,
        )

        # Assert
        self.assertIn(
            (
                "/srv/shop",
                (
                    *ADD_A_CHECKOUT_OF_THE_TASK_HEAD,
                    str(self.paths.state_root / "head-checks" / "shop" / TASK_HEAD),
                    TASK_HEAD,
                ),
            ),
            runner.commands,
        )

    def test_should_hold_a_branch_whose_pull_request_checks_are_pending_with_no_rebase_and_no_setup(self):
        # Arrange
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner),
            Configuration(),
            ACTION_WITH_PENDING_PULL_REQUEST_CHECKS,
            NO_FORGE,
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1"),
                conflicted=False,
                on_start=False,
                held_by=HoldingHead(
                    branch="feature/B1-task", proof=HeadProof(commit=TASK_HEAD, state="pending", failed_commands=())
                ),
            ),
        )
        self.assertNotIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)
        self.assertNotIn((str(WORKTREE), ("make", "deps")), runner.commands)

    def test_should_hold_a_green_branch_off_a_red_wave_branch_with_no_rebase_and_no_setup(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        self.record_commit_checks(WAVE_HEAD, exit_code=1)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1"),
                conflicted=False,
                on_start=False,
                held_by=HoldingHead(
                    branch="integration/w1",
                    proof=HeadProof(commit=WAVE_HEAD, state="red", failed_commands=("make test",)),
                ),
            ),
        )
        self.assertNotIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)
        self.assertNotIn((str(WORKTREE), ("make", "deps")), runner.commands)

    def test_should_leave_a_branch_descending_from_the_wave_branch_unrebased(self):
        # Arrange
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_WORKTREE_LISTED, branch=TASK_BRANCH_FOUND)

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertNotIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)

    def test_should_abort_a_rebase_stopped_on_a_conflict_and_run_no_setup(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=0)
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(
            MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers={**OFF_THE_WAVE_BRANCH, **STOPPED_ON_A_CONFLICT}
        )

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertTrue(prepared.conflicted)
        self.assertEqual(runner.commands[-1], (str(WORKTREE), ("git", "rebase", "--abort")))


class PrepareTaskWorktreeOfARedBranchOffTheWaveBranchTest(PrepareTaskWorktreeTestCase):
    def test_should_run_the_setup_on_the_branch_as_it_stands_without_rebasing_it_or_requiring_the_wave_branch(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=1)
        self.record_commit_checks(WAVE_HEAD, exit_code=0)
        runner = self.create_runner(
            MAKE_DEPS,
            branch=TASK_BRANCH_FOUND,
            answers={**OFF_THE_WAVE_BRANCH, REQUIRE_THE_WAVE_BRANCH: HEAD_OFF_THE_WAVE_BRANCH},
        )

        # Act
        prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertNotIn((str(WORKTREE), REBASE_ON_THE_WAVE_BRANCH), runner.commands)
        self.assertEqual(runner.commands[-1], (str(WORKTREE), ("make", "deps")))

    def test_should_hand_over_the_worktree_off_its_start_with_the_commands_that_failed_at_its_head(self):
        # Arrange
        self.record_commit_checks(TASK_HEAD, exit_code=1)
        runner = self.create_runner(MAKE_DEPS, branch=TASK_BRANCH_FOUND, answers=OFF_THE_WAVE_BRANCH)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1"),
                conflicted=False,
                on_start=False,
                rebased=False,
                failed_commands=("make test",),
            ),
        )


CANCELLATION_INSTANT = datetime(2026, 10, 28, 19, 40, tzinfo=UTC)
WAVE_OF_THE_PREVIOUS_ATTEMPT = WaveStarted(wave="w0", project="shop", branch="integration/w0", tasks=("B1",))


class PrepareTaskWorktreeOfATaskLaunchedAgainAfterACancelTest(PrepareTaskWorktreeTestCase):
    def test_should_take_over_the_branch_of_the_task_its_worktree_holds(self):
        # Arrange
        append_event(self.paths, CANCELLATION_INSTANT, WAVE_OF_THE_PREVIOUS_ATTEMPT)
        append_event(self.paths, CANCELLATION_INSTANT, WaveCancelled(wave="w0", reason="user"))
        runner = self.create_runner(MAKE_DEPS, worktrees=TASK_WORKTREE_LISTED, branch=TASK_BRANCH_FOUND)

        # Act
        prepared = prepare_task_worktree(
            create_test_runtime(self.paths, run_process=runner), Configuration(), ACTION, NO_FORGE
        )

        # Assert
        self.assertEqual(
            prepared,
            PreparedWorktree(
                worktree=BranchWorktree(path=WORKTREE, branch="feature/B1-task", start="integration/w1"),
                conflicted=False,
                on_start=True,
            ),
        )
        self.assertEqual(
            runner.commands[-4:],
            [
                ("/srv/shop", LIST_WORKTREES),
                (str(WORKTREE), TASK_BRANCH_DESCENDS),
                (str(WORKTREE), ("make", "deps")),
                (str(WORKTREE), REQUIRE_THE_WAVE_BRANCH),
            ],
        )
