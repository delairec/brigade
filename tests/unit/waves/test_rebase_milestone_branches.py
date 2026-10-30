import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.run_process import ProcessRequest
from brigade.waves.read_project_tasks import ProjectTasks
from brigade.waves.rebase_milestone_branches import BranchRebaseRun, MilestoneBranchesRebase, rebase_milestone_branches
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_argvs_run_in import select_argvs_run_in
from tests.unit.select_commands_opening_on import select_commands_opening_on

REPOSITORY = "/srv/shop"
MILESTONE_BRANCH = "integration/dashboard"
MILESTONE_WORKTREE = "/srv/shop/.brigade/worktrees/integration-dashboard"
WAVE_WORKTREE = "/srv/shop/.brigade/worktrees/integration-shop_w1"
MILESTONE_HEAD = "5e2a7c1"
WAVE_HEAD = "c3d9f04"
STOPPED_ON_A_CONFLICT = 1
NOT_AN_ANCESTOR = 1
REBASE_IN_PROGRESS = 0
GIT = ("git",)
GIT_REBASE = ("git", "rebase")
GIT_PUSH = ("git", "push")
GIT_RESET = ("git", "reset")
TASKS_AT_MAIN = {
    "S7": Entity(name="S7", fields=(EntityField(name="STATUS", value="todo"),)),
    "S20": Entity(name="S20", fields=(EntityField(name="MILESTONE", value="@MILESTONE.M3"),)),
}
CUT_OF_M3 = {
    "schema_version": 1,
    "ts": "2026-10-28T09:00:00Z",
    "event": "milestone.branch_cut",
    "project": "shop",
    "milestone": "M3",
    "branch": MILESTONE_BRANCH,
    "login": "octo-bot",
}
OPEN_WAVE_OF_M3 = {
    "schema_version": 2,
    "ts": "2026-10-28T10:00:00Z",
    "event": "wave.started",
    "wave": "shop_w1",
    "project": "shop",
    "branch": "integration/shop_w1",
    "tasks": ["S20"],
}
OPEN_WAVE_OF_NO_MILESTONE = {
    "schema_version": 2,
    "ts": "2026-10-28T11:00:00Z",
    "event": "wave.started",
    "wave": "shop_w2",
    "project": "shop",
    "branch": "integration/shop_w2",
    "tasks": ["S7"],
}
ACTIVE_M3 = {"entities": [{"type": "MILESTONE", "name": "M3"}]}
NO_ACTIVE_MILESTONE = {"entities": []}
NO_WORKTREE = ""
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli-key"}


def _read_forge_environment(key: str) -> dict:
    return FORGE_ENVIRONMENT


def _create_project(forge: str) -> Entity:
    return Entity(
        name="shop",
        fields=(
            EntityField(name="PATH", value=REPOSITORY),
            EntityField(name="MAIN", value="main"),
            EntityField(name="FORGE", value=forge),
        ),
    )


class RebaseMilestoneBranchesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.tree = self.root / "cache" / "refs" / "shop" / "4f1c2a9"
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.launched: list[BranchRebaseRun] = []
        self.live_worktrees: set[Path] = set()
        self.rebase_exit_codes = {MILESTONE_WORKTREE: 0, WAVE_WORKTREE: 0}
        self.wave_descent = NOT_AN_ANCESTOR
        write_ledger(self.root, [CUT_OF_M3, OPEN_WAVE_OF_M3, OPEN_WAVE_OF_NO_MILESTONE])
        self.answer_active_milestones(ACTIVE_M3)
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=NO_WORKTREE)
        self.processes.answer(("git", "worktree", "add", "--quiet", MILESTONE_WORKTREE, MILESTONE_BRANCH))
        self.processes.answer(("git", "worktree", "add", "--quiet", WAVE_WORKTREE, "integration/shop_w1"))
        self.processes.answer_by(("git", "rev-parse", "HEAD"), self.answer_head)
        self.processes.answer_by(
            ("git", "merge-base", "--is-ancestor", MILESTONE_BRANCH, "HEAD"),
            lambda request: (self.wave_descent, "", ""),
        )
        self.processes.answer(("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"), exit_code=REBASE_IN_PROGRESS)
        self.processes.answer(("git", "rebase", "--abort"))
        for branch, head in ((MILESTONE_BRANCH, MILESTONE_HEAD), ("integration/shop_w1", WAVE_HEAD)):
            self.processes.answer(
                ("git", "push", "--quiet", f"--force-with-lease={branch}:{head}", "origin", f"HEAD:{branch}")
            )

    def answer_head(self, request: ProcessRequest) -> tuple[int, str, str]:
        return 0, f"{MILESTONE_HEAD if request.cwd == MILESTONE_WORKTREE else WAVE_HEAD}\n", ""

    def answer_rebase(self, request: ProcessRequest) -> tuple[int, str, str]:
        return self.rebase_exit_codes[request.cwd], "", ""

    def answer_active_milestones(self, document: dict) -> None:
        self.processes.answer_json(
            ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json", str(self.tree)), document
        )

    def register_project(self, forge: str) -> Entity:
        self.processes.answer(("git", "fetch", "--quiet", "origin", "main"))
        self.processes.answer(("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH))
        self.processes.answer(("git", "fetch", "--quiet", "origin", "integration/shop_w1"))
        self.processes.answer(("git", "reset", "--quiet", "--hard", "origin/integration/dashboard"))
        self.processes.answer(("git", "reset", "--quiet", "--hard", "origin/integration/shop_w1"))
        self.processes.answer(("git", "reset", "--quiet", "--hard", MILESTONE_BRANCH))
        self.processes.answer(("git", "reset", "--quiet", "--hard", "integration/shop_w1"))
        self.processes.answer_by(("git", "rebase", "origin/main"), self.answer_rebase)
        self.processes.answer_by(("git", "rebase", "main"), self.answer_rebase)
        self.processes.answer_by(("git", "rebase", MILESTONE_BRANCH), self.answer_rebase)
        return _create_project(forge)

    def rebase(self, forge: str = "github") -> None:
        project = self.register_project(forge)
        rebase = MilestoneBranchesRebase(
            project=project,
            tasks=ProjectTasks(root=self.tree, by_name=TASKS_AT_MAIN, implemented=frozenset()),
            worktree_root=None,
            read_environment=_read_forge_environment,
            is_run_live_on=lambda worktree: worktree in self.live_worktrees,
            launch_rebase_run=self.launched.append,
        )
        rebase_milestone_branches(self.runtime, rebase)


class RebaseMilestoneBranchesOntoTheMainBranchTest(RebaseMilestoneBranchesTestCase):
    def test_should_rebase_the_milestone_branch_of_the_forge_onto_the_main_branch_of_the_forge(self):
        # Arrange
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_RESET)[0],
            (MILESTONE_WORKTREE, ("git", "reset", "--quiet", "--hard", "origin/integration/dashboard")),
        )
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [(MILESTONE_WORKTREE, ("git", "rebase", "origin/main"))],
        )

    def test_should_rebase_in_the_worktree_the_milestone_branch_already_holds_without_adding_one(self):
        # Arrange
        self.wave_descent = 0
        self.processes.answer(
            ("git", "worktree", "list", "--porcelain", "-z"),
            stdout=f"worktree {MILESTONE_WORKTREE}\0HEAD {MILESTONE_HEAD}\0branch refs/heads/{MILESTONE_BRANCH}\0\0",
        )

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, ("git", "worktree", "add")),
            [(REPOSITORY, ("git", "worktree", "add", "--quiet", WAVE_WORKTREE, "integration/shop_w1"))],
        )
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [(MILESTONE_WORKTREE, ("git", "rebase", "origin/main"))],
        )

    def test_should_add_the_worktree_of_the_milestone_branch_where_its_place_holds_another_branch(self):
        # Arrange
        self.wave_descent = 0
        self.processes.answer(
            ("git", "worktree", "list", "--porcelain", "-z"),
            stdout=f"worktree {MILESTONE_WORKTREE}\0HEAD {MILESTONE_HEAD}\0branch refs/heads/task/shop_w1/S20\0\0",
        )

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, ("git", "worktree", "add"))[0],
            (REPOSITORY, ("git", "worktree", "add", "--quiet", MILESTONE_WORKTREE, MILESTONE_BRANCH)),
        )

    def test_should_push_the_rebased_milestone_branch_with_a_lease_on_its_head_on_the_forge(self):
        # Arrange
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_PUSH),
            [
                (
                    MILESTONE_WORKTREE,
                    (
                        "git",
                        "push",
                        "--quiet",
                        "--force-with-lease=integration/dashboard:5e2a7c1",
                        "origin",
                        "HEAD:integration/dashboard",
                    ),
                )
            ],
        )

    def test_should_rebase_the_local_milestone_branch_onto_the_local_main_branch_without_a_forge(self):
        # Arrange
        self.wave_descent = 0

        # Act
        self.rebase("none")

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [(MILESTONE_WORKTREE, ("git", "rebase", "main"))],
        )

    def test_should_push_nothing_without_a_forge(self):
        # Act
        self.rebase("none")

        # Assert
        self.assertEqual(select_commands_opening_on(self.processes.requests, GIT_PUSH), [])

    def test_should_rebase_nothing_for_a_milestone_whose_branch_is_not_cut(self):
        # Arrange
        write_ledger(self.root, [OPEN_WAVE_OF_NO_MILESTONE])

        # Act
        self.rebase()

        # Assert
        self.assertEqual(self.processes.list_argvs(), [])

    def test_should_rebase_nothing_for_a_milestone_whose_branch_another_project_cut(self):
        # Arrange
        write_ledger(self.root, [{**CUT_OF_M3, "project": "depot"}, OPEN_WAVE_OF_M3])

        # Act
        self.rebase()

        # Assert
        self.assertEqual(self.processes.list_argvs(), [])

    def test_should_rebase_nothing_for_a_milestone_that_is_not_active(self):
        # Arrange
        self.answer_active_milestones(NO_ACTIVE_MILESTONE)

        # Act
        self.rebase()

        # Assert
        self.assertEqual(select_commands_opening_on(self.processes.requests, GIT), [])

    def test_should_rebase_under_the_worktrees_lock_of_the_project(self):
        # Arrange
        held = []

        def answer_rebase_with_the_lock_tried(request: ProcessRequest) -> tuple[int, str, str]:
            with hold_lock_without_waiting(self.root / "state" / "locks" / "worktrees-shop.lock") as acquired:
                held.append(not acquired)
            return 0, "", ""

        self.wave_descent = 0
        project = self.register_project("github")
        self.processes.answer_by(("git", "rebase", "origin/main"), answer_rebase_with_the_lock_tried)
        rebase = MilestoneBranchesRebase(
            project=project,
            tasks=ProjectTasks(root=self.tree, by_name=TASKS_AT_MAIN, implemented=frozenset()),
            worktree_root=None,
            read_environment=_read_forge_environment,
            is_run_live_on=lambda worktree: False,
            launch_rebase_run=self.launched.append,
        )

        # Act
        rebase_milestone_branches(self.runtime, rebase)

        # Assert
        self.assertEqual(held, [True])


class RebaseMilestoneBranchesWithTheirOpenWavesTest(RebaseMilestoneBranchesTestCase):
    def test_should_rebase_an_open_wave_of_the_milestone_off_its_rebased_branch_onto_it(self):
        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [
                (MILESTONE_WORKTREE, ("git", "rebase", "origin/main")),
                (WAVE_WORKTREE, ("git", "rebase", MILESTONE_BRANCH)),
            ],
        )

    def test_should_push_the_rebased_wave_branch_with_a_lease_on_its_head(self):
        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_PUSH)[1],
            (
                WAVE_WORKTREE,
                (
                    "git",
                    "push",
                    "--quiet",
                    "--force-with-lease=integration/shop_w1:c3d9f04",
                    "origin",
                    "HEAD:integration/shop_w1",
                ),
            ),
        )

    def test_should_leave_an_open_wave_that_descends_from_the_rebased_milestone_branch(self):
        # Arrange
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            select_commands_opening_on(self.processes.requests, GIT_REBASE),
            [(MILESTONE_WORKTREE, ("git", "rebase", "origin/main"))],
        )


class RebaseMilestoneBranchesStoppedOnAConflictTest(RebaseMilestoneBranchesTestCase):
    def test_should_abort_the_rebase_of_the_milestone_branch_and_launch_a_rebase_run_onto_the_main_branch(self):
        # Arrange
        self.rebase_exit_codes[MILESTONE_WORKTREE] = STOPPED_ON_A_CONFLICT
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            self.launched,
            [
                BranchRebaseRun(
                    project="shop", worktree=Path(MILESTONE_WORKTREE), branch=MILESTONE_BRANCH, base="main", wave=None
                )
            ],
        )

    def test_should_push_no_branch_whose_rebase_stopped(self):
        # Arrange
        self.rebase_exit_codes[MILESTONE_WORKTREE] = STOPPED_ON_A_CONFLICT
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(select_commands_opening_on(self.processes.requests, GIT_PUSH), [])

    def test_should_launch_a_rebase_run_of_the_wave_branch_onto_the_milestone_branch(self):
        # Arrange
        self.rebase_exit_codes[WAVE_WORKTREE] = STOPPED_ON_A_CONFLICT

        # Act
        self.rebase()

        # Assert
        self.assertEqual(
            self.launched,
            [
                BranchRebaseRun(
                    project="shop",
                    worktree=Path(WAVE_WORKTREE),
                    branch="integration/shop_w1",
                    base=MILESTONE_BRANCH,
                    wave="shop_w1",
                )
            ],
        )

    def test_should_touch_no_wave_branch_whose_worktree_a_live_run_holds(self):
        # Arrange
        self.live_worktrees = {Path(WAVE_WORKTREE)}

        # Act
        self.rebase()

        # Assert
        self.assertEqual(select_argvs_run_in(self.processes.requests, WAVE_WORKTREE), [])

    def test_should_touch_no_branch_whose_worktree_a_live_run_holds(self):
        # Arrange
        self.live_worktrees = {Path(MILESTONE_WORKTREE)}
        self.wave_descent = 0

        # Act
        self.rebase()

        # Assert
        self.assertEqual(select_argvs_run_in(self.processes.requests, MILESTONE_WORKTREE), [])
