import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.waves.cut_milestone_branch import MilestoneBranchDemand, cut_milestone_branch
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_argvs_opening_on import select_argvs_opening_on

REPOSITORY = "/srv/shop"
BRANCH = "integration/milestone-integration-branch"
BRANCH_NOT_FOUND = 1
GIT_BRANCH = ("git", "branch")
GIT_PUSH = ("git", "push")
PUSH_REFUSED = 1
REMOTE_BRANCH_NOT_FOUND = 2
LS_REMOTE = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", f"refs/heads/{BRANCH}")
PUSH_OF_MAIN_TO_THE_BRANCH = ("git", "push", "--quiet", "origin", f"origin/main:refs/heads/{BRANCH}")
MILESTONE = Entity(name="M9", fields=(EntityField(name="TITLE", value="Milestone integration branch"),))
RETITLED_MILESTONE = Entity(name="M9", fields=(EntityField(name="TITLE", value="One branch per milestone"),))
CUT_OF_M9 = {
    "schema_version": 1,
    "ts": "2026-10-28T09:00:00Z",
    "event": "milestone.branch_cut",
    "project": "shop",
    "milestone": "M9",
    "branch": BRANCH,
    "login": None,
}
CUT_OF_M3 = CUT_OF_M9 | {"milestone": "M3"}
CUT_IN_ANOTHER_PROJECT = CUT_OF_M9 | {"project": "blog", "milestone": "M3"}


def _create_project(forge: str) -> Entity:
    return Entity(
        name="shop",
        fields=(
            EntityField(name="PATH", value=REPOSITORY),
            EntityField(name="MAIN", value="main"),
            EntityField(name="FORGE", value=forge),
        ),
    )


def _read_forge_environment(slot: str) -> dict:
    return {"GH_TOKEN": f"token-of-the-{slot}-key"}


def _read_login() -> str:
    return "octo-bot"


def _fail_to_read_login() -> str:
    raise BrigadeError("the forge answers no login for the cli key")


class CutMilestoneBranchTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        write_ledger(self.root, [])
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"), exit_code=1)
        self.processes.answer(LS_REMOTE, exit_code=REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(("git", "branch", "--quiet", BRANCH, "main"))
        self.processes.answer(("git", "fetch", "--quiet", "origin", "main"))
        self.processes.answer(("git", "branch", "--quiet", BRANCH, "origin/main"))
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH))

    def cut(self, forge: str, milestone: Entity = MILESTONE, read_login: Callable[[], str] = _read_login) -> str:
        demand = MilestoneBranchDemand(
            project=_create_project(forge),
            milestone=milestone,
            read_environment=_read_forge_environment,
            read_login=read_login,
        )
        return cut_milestone_branch(self.runtime, demand)

    def read_events(self) -> list[dict]:
        ledger = self.root / "state" / "ledger" / "2026-10.jsonl"
        return list(map(json.loads, ledger.read_text(encoding="utf-8").splitlines()))

    def list_git_writes(self) -> list[tuple[str, ...]]:
        return select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH, GIT_PUSH)


class CutMilestoneBranchWithoutAForgeTest(CutMilestoneBranchTestCase):
    def test_should_cut_the_branch_named_after_the_title_from_the_main_branch(self):
        # Act
        branch = self.cut("none")

        # Assert
        self.assertEqual(branch, BRANCH)
        self.assertEqual(self.list_git_writes(), [("git", "branch", "--quiet", BRANCH, "main")])

    def test_should_record_the_cut_of_the_branch_with_no_login(self):
        # Act
        self.cut("none")

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.branch_cut",
                    "project": "shop",
                    "milestone": "M9",
                    "branch": BRANCH,
                    "login": None,
                }
            ],
        )


class CutMilestoneBranchOnTheGithubForgeTest(CutMilestoneBranchTestCase):
    def test_should_cut_the_branch_from_the_main_branch_of_the_forge_and_push_it(self):
        # Act
        self.cut("github")

        # Assert
        self.assertEqual(
            self.list_git_writes(),
            [("git", "branch", "--quiet", BRANCH, "origin/main"), ("git", "push", "--quiet", "origin", BRANCH)],
        )

    def test_should_record_the_login_of_the_cli_key(self):
        # Act
        self.cut("github")

        # Assert
        self.assertEqual(self.read_events()[0]["login"], "octo-bot")

    def test_should_delete_the_branch_it_cut_and_record_nothing_when_the_push_fails(self):
        # Arrange
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH), exit_code=PUSH_REFUSED)
        self.processes.answer(("git", "branch", "--quiet", "-D", BRANCH))

        # Act
        with self.assertRaises(BrigadeError):
            self.cut("github")

        # Assert
        self.assertEqual(
            self.list_git_writes(),
            [
                ("git", "branch", "--quiet", BRANCH, "origin/main"),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("git", "branch", "--quiet", "-D", BRANCH),
            ],
        )
        self.assertEqual(self.read_events(), [])

    def test_should_cut_and_push_nothing_when_the_login_cannot_be_read(self):
        # Act
        with self.assertRaises(BrigadeError):
            self.cut("github", read_login=_fail_to_read_login)

        # Assert
        self.assertEqual(self.list_git_writes(), [])
        self.assertEqual(self.read_events(), [])

    def test_should_refuse_a_branch_of_the_name_the_forge_holds_and_no_cut_records(self):
        # Arrange
        self.processes.answer(LS_REMOTE)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.cut("github")

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"@MILESTONE.M9: the branch {BRANCH} exists and no milestone.branch_cut records it",
        )


class CutMilestoneBranchAlreadyRecordedTest(CutMilestoneBranchTestCase):
    def test_should_answer_the_recorded_branch_of_a_retitled_milestone_and_cut_nothing(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M9])
        self.processes.answer(LS_REMOTE)

        # Act
        branch = self.cut("github", RETITLED_MILESTONE)

        # Assert
        self.assertEqual(branch, BRANCH)
        self.assertEqual(self.list_git_writes(), [])
        self.assertEqual(self.read_events(), [CUT_OF_M9])

    def test_should_refuse_the_name_another_milestone_of_the_project_records(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M3])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.cut("none")

        # Assert
        self.assertEqual(str(refusal.exception), f"@MILESTONE.M9: the branch {BRANCH} is the branch of @MILESTONE.M3")
        self.assertEqual(self.list_git_writes(), [])

    def test_should_cut_the_name_another_project_records_for_its_milestone(self):
        # Arrange
        write_ledger(self.root, [CUT_IN_ANOTHER_PROJECT])

        # Act
        branch = self.cut("none")

        # Assert
        self.assertEqual(branch, BRANCH)

    def test_should_refuse_a_branch_of_the_name_the_clone_holds_and_no_cut_records(self):
        # Arrange
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.cut("none")

        # Assert
        self.assertEqual(
            str(refusal.exception), f"@MILESTONE.M9: the branch {BRANCH} exists and no milestone.branch_cut records it"
        )
        self.assertEqual(self.list_git_writes(), [])


class CutMilestoneBranchTheForgeDeletedTest(CutMilestoneBranchTestCase):
    def setUp(self):
        super().setUp()
        write_ledger(self.root, [CUT_OF_M9])
        self.processes.answer(PUSH_OF_MAIN_TO_THE_BRANCH)

    def test_should_cut_the_recorded_branch_again_from_the_main_branch_of_the_forge(self):
        # Act
        branch = self.cut("github", RETITLED_MILESTONE)

        # Assert
        self.assertEqual(branch, BRANCH)
        self.assertEqual(self.list_git_writes(), [PUSH_OF_MAIN_TO_THE_BRANCH])

    def test_should_record_the_new_cut_with_the_login_of_the_cli_key(self):
        # Act
        self.cut("github")

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                CUT_OF_M9,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.branch_cut",
                    "project": "shop",
                    "milestone": "M9",
                    "branch": BRANCH,
                    "login": "octo-bot",
                },
            ],
        )

    def test_should_push_and_record_nothing_when_the_login_cannot_be_read(self):
        # Act
        with self.assertRaises(BrigadeError):
            self.cut("github", read_login=_fail_to_read_login)

        # Assert
        self.assertEqual(self.list_git_writes(), [])
        self.assertEqual(self.read_events(), [CUT_OF_M9])
