import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.ledger.wave_rebased import WaveRebased
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.run_process import ProcessRequest
from brigade.waves.rebase_milestone_branches import BranchRebaseRun
from brigade.waves.rebase_wave_branch import WaveBranchRebase, rebase_wave_branch
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_argvs_run_in import select_argvs_run_in
from tests.unit.select_commands_opening_on import select_commands_opening_on

REPOSITORY = "/srv/shop"
MILESTONE_BRANCH = "integration/dashboard"
WAVE_BRANCH = "integration/shop_w4"
WAVE_WORKTREE = "/srv/shop/.brigade/worktrees/integration-shop_w4"
WAVE_HEAD = "c3d9f04"
REBASED_WAVE_HEAD = "e70f3a2"
CLEAN_REBASE = 0
STOPPED_ON_A_CONFLICT = 1
REBASE_IN_PROGRESS = 0
GIT_REBASE = ("git", "rebase")
GIT_PUSH = ("git", "push")
GIT_RESET = ("git", "reset")
NO_WORKTREE = ""
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli-key"}


def _read_forge_environment(key: str) -> dict:
    return FORGE_ENVIRONMENT


def _read_login() -> str:
    return "octo-bot"


def _fail_to_read_login() -> str:
    raise BrigadeError("gh api user failed")


def _create_project(forge: str) -> Entity:
    return Entity(
        name="shop",
        fields=(
            EntityField(name="PATH", value=REPOSITORY),
            EntityField(name="MAIN", value="main"),
            EntityField(name="FORGE", value=forge),
        ),
    )


class RebaseWaveBranchTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.launched: list[BranchRebaseRun] = []
        self.live_worktrees: set[Path] = set()
        self.rebase_exit_code = CLEAN_REBASE
        self.head_after_rebase = REBASED_WAVE_HEAD
        self.rebased = False
        self.read_login = _read_login
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=NO_WORKTREE)
        self.processes.answer(("git", "worktree", "add", "--quiet", WAVE_WORKTREE, WAVE_BRANCH))
        self.processes.answer_by(("git", "rev-parse", "HEAD"), self.answer_head)
        self.processes.answer(("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"), exit_code=REBASE_IN_PROGRESS)
        self.processes.answer(("git", "rebase", "--abort"))
        self.processes.answer(("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH))
        self.processes.answer(("git", "fetch", "--quiet", "origin", WAVE_BRANCH))
        self.processes.answer(("git", "reset", "--quiet", "--hard", "origin/integration/shop_w4"))
        self.processes.answer(("git", "reset", "--quiet", "--hard", WAVE_BRANCH))
        self.processes.answer_by(("git", "rebase", "origin/integration/dashboard"), self.answer_rebase)
        self.processes.answer_by(("git", "rebase", MILESTONE_BRANCH), self.answer_rebase)
        self.processes.answer(
            ("git", "push", "--quiet", f"--force-with-lease={WAVE_BRANCH}:{WAVE_HEAD}", "origin", f"HEAD:{WAVE_BRANCH}")
        )

    def answer_head(self, request: ProcessRequest) -> tuple[int, str, str]:
        return 0, f"{self.head_after_rebase if self.rebased else WAVE_HEAD}\n", ""

    def answer_rebase(self, request: ProcessRequest) -> tuple[int, str, str]:
        self.rebased = self.rebase_exit_code == CLEAN_REBASE
        return self.rebase_exit_code, "", ""

    def rebase(self, forge: str = "github") -> WaveRebased | None:
        rebase = WaveBranchRebase(
            project=_create_project(forge),
            wave="shop_w4",
            branch=WAVE_BRANCH,
            base=MILESTONE_BRANCH,
            worktree_root=None,
            read_environment=_read_forge_environment,
            is_run_live_on=lambda worktree: worktree in self.live_worktrees,
            launch_rebase_run=self.launched.append,
            read_login=self.read_login,
        )
        return rebase_wave_branch(self.runtime, rebase)


class RebaseWaveBranchOntoItsMilestoneBranchTest(RebaseWaveBranchTestCase):
    def test_should_rebase_the_wave_branch_of_the_forge_onto_the_milestone_branch_of_the_forge(self):
        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_RESET),
            [(WAVE_WORKTREE, ("git", "reset", "--quiet", "--hard", "origin/integration/shop_w4"))],
        )
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [(WAVE_WORKTREE, ("git", "rebase", "origin/integration/dashboard"))],
        )

    def test_should_push_the_rebased_wave_branch_with_a_lease_on_its_head_on_the_forge(self):
        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_PUSH),
            [
                (
                    WAVE_WORKTREE,
                    (
                        "git",
                        "push",
                        "--quiet",
                        "--force-with-lease=integration/shop_w4:c3d9f04",
                        "origin",
                        "HEAD:integration/shop_w4",
                    ),
                )
            ],
        )

    def test_should_rebase_the_local_wave_branch_onto_the_local_milestone_branch_and_push_nothing_without_a_forge(
        self,
    ):
        # Act
        self.rebase("none")

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, (*GIT_REBASE, MILESTONE_BRANCH))
            + select_commands_opening_on(self.processes.requests, GIT_PUSH),
            [(WAVE_WORKTREE, ("git", "rebase", "integration/dashboard"))],
        )

    def test_should_rebase_under_the_worktrees_lock_of_the_project(self):
        # Arrange
        held = []

        def answer_rebase_with_the_lock_tried(request: ProcessRequest) -> tuple[int, str, str]:
            with hold_lock_without_waiting(self.root / "state" / "locks" / "worktrees-shop.lock") as acquired:
                held.append(not acquired)
            return CLEAN_REBASE, "", ""

        self.processes.answer_by(("git", "rebase", "origin/integration/dashboard"), answer_rebase_with_the_lock_tried)

        # Act
        self.rebase()

        # Assert
        self.assertEqual(held, [True])

    def test_should_rebase_nothing_when_the_login_of_the_cli_cannot_be_read(self):
        # Arrange
        self.read_login = _fail_to_read_login

        # Act
        with self.assertRaises(BrigadeError):
            self.rebase()

        # Assert
        self.assertEqual(select_commands_opening_on(self.processes.requests, GIT_REBASE), [])


class RebaseWaveBranchStoppedOnAConflictTest(RebaseWaveBranchTestCase):
    def test_should_launch_a_rebase_run_of_the_wave_branch_onto_its_milestone_branch(self):
        # Arrange
        self.rebase_exit_code = STOPPED_ON_A_CONFLICT

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            self.launched,
            [
                BranchRebaseRun(
                    project="shop",
                    worktree=Path(WAVE_WORKTREE),
                    branch=WAVE_BRANCH,
                    base=MILESTONE_BRANCH,
                    wave="shop_w4",
                )
            ],
        )

    def test_should_push_nothing_and_answer_no_rebase(self):
        # Arrange
        self.rebase_exit_code = STOPPED_ON_A_CONFLICT

        # Act
        rebased = self.rebase()

        # Assert
        self.assertIsNone(rebased)
        self.assertEqual(select_commands_opening_on(self.processes.requests, GIT_PUSH), [])

    def test_should_touch_no_wave_branch_whose_worktree_a_live_run_holds(self):
        # Arrange
        self.live_worktrees = {Path(WAVE_WORKTREE)}

        # Act
        rebased = self.rebase()

        # Assert
        self.assertIsNone(rebased)
        self.assertEqual(select_argvs_run_in(self.processes.requests, WAVE_WORKTREE), [])
        self.assertEqual(self.launched, [])


class RebaseWaveBranchRecordedTest(RebaseWaveBranchTestCase):
    def test_should_answer_the_clean_rebase_of_the_wave_branch_with_its_heads_before_and_after(self):
        # Act
        rebased = self.rebase()

        # Assert
        self.assertEqual(
            rebased,
            WaveRebased(
                project="shop",
                wave="shop_w4",
                branch=WAVE_BRANCH,
                before="c3d9f04",
                after="e70f3a2",
                login="octo-bot",
            ),
        )

    def test_should_answer_the_clean_rebase_with_no_login_without_a_forge(self):
        # Act
        rebased = self.rebase("none")

        # Assert
        self.assertEqual(
            rebased,
            WaveRebased(
                project="shop", wave="shop_w4", branch=WAVE_BRANCH, before="c3d9f04", after="e70f3a2", login=None
            ),
        )

    def test_should_answer_no_rebase_when_the_rebase_left_the_head_of_the_wave_branch_where_it_was(self):
        # Arrange
        self.head_after_rebase = WAVE_HEAD

        # Act
        rebased = self.rebase()

        # Assert
        self.assertIsNone(rebased)
