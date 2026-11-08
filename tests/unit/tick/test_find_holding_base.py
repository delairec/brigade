import json
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.tick.actions import LaunchTask, RebaseMilestone, RebaseTask
from brigade.tick.find_holding_base import find_holding_base
from brigade.tick.head_proof import HeadProof, HoldingHead
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LOCAL_PROJECT = Entity(
    name="oak",
    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="MAIN", value="main")),
)
GITHUB_PROJECT = Entity(
    name="oak",
    fields=(
        EntityField(name="PATH", value="/srv/oak"),
        EntityField(name="MAIN", value="main"),
        EntityField(name="FORGE", value="github"),
    ),
)
BASE_HEAD = "8885daa"
TASK_HEAD = "4c0e214"
LAUNCH = LaunchTask(
    project="oak",
    wave="oak_w3",
    branch="integration/M4",
    task="T7",
    task_branch="feature/T7-tide-table",
    pull_request_checks=None,
)
CATCH_UP = RebaseTask(
    project="oak",
    wave="oak_w3",
    branch="integration/M4",
    task="T7",
    task_branch="feature/T7-tide-table",
    pr=12,
    worktree="/srv/oak/.brigade/worktrees/T7",
    head=TASK_HEAD,
    holds_uncommitted_changes=False,
)
MILESTONE_REBASE = RebaseMilestone(project="oak", milestone="M4", branch="integration/M4")


def resolve(ref: str) -> tuple[str, ...]:
    return ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")


TASK_BRANCH_OFF_THE_BASE = {
    resolve("feature/T7-tide-table"): ProcessAnswer(stdout=f"{TASK_HEAD}\n"),
    ("git", "merge-base", "--is-ancestor", "integration/M4", "feature/T7-tide-table"): ProcessAnswer(exit_code=1),
    resolve("integration/M4"): ProcessAnswer(stdout=f"{BASE_HEAD}\n"),
}
NO_CHECK_RUN: list[dict] = []


def list_no_check_run(repository: str, branch: str) -> list[dict]:
    return NO_CHECK_RUN


def list_a_pending_check_run(repository: str, branch: str) -> list[dict]:
    return [{"head": BASE_HEAD, "name": "unit", "conclusion": "pending"}]


class FindHoldingBaseTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = create_test_paths(Path(directory.name))

    def _record_checks(self, exit_code: int) -> None:
        record = self.paths.state_root / "commit-checks" / "oak" / f"{BASE_HEAD}.json"
        record.parent.mkdir(parents=True)
        record.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": "oak",
                    "commit": BASE_HEAD,
                    "checks": [{"command": "make test", "exit_code": exit_code}],
                }
            ),
            encoding="utf-8",
        )

    def _find(self, project: Entity, action, answers: dict, list_check_runs=list_no_check_run) -> HoldingHead | None:
        runtime = create_test_runtime(self.paths, run_process=RecordingProcessRunner(answers))
        return find_holding_base(runtime, project, action, list_check_runs)

    def test_should_name_the_red_base_of_a_task_branch_off_it(self):
        # Arrange
        self._record_checks(1)

        # Act
        held_by = self._find(LOCAL_PROJECT, LAUNCH, TASK_BRANCH_OFF_THE_BASE)

        # Assert
        self.assertEqual(
            held_by,
            HoldingHead(
                branch="integration/M4",
                proof=HeadProof(commit=BASE_HEAD, state="red", failed_commands=("make test",)),
            ),
        )

    def test_should_hold_nothing_on_a_green_base(self):
        # Arrange
        self._record_checks(0)

        # Act
        held_by = self._find(LOCAL_PROJECT, LAUNCH, TASK_BRANCH_OFF_THE_BASE)

        # Assert
        self.assertIsNone(held_by)

    def test_should_hold_nothing_for_a_task_whose_branch_does_not_exist_yet(self):
        # Arrange
        self._record_checks(1)
        no_task_branch = {**TASK_BRANCH_OFF_THE_BASE, resolve("feature/T7-tide-table"): ProcessAnswer(exit_code=1)}

        # Act
        held_by = self._find(LOCAL_PROJECT, LAUNCH, no_task_branch)

        # Assert
        self.assertIsNone(held_by)

    def test_should_hold_nothing_for_a_task_branch_descending_from_its_base(self):
        # Arrange
        self._record_checks(1)
        descending = {
            **TASK_BRANCH_OFF_THE_BASE,
            ("git", "merge-base", "--is-ancestor", "integration/M4", "feature/T7-tide-table"): ProcessAnswer(),
        }

        # Act
        held_by = self._find(LOCAL_PROJECT, LAUNCH, descending)

        # Assert
        self.assertIsNone(held_by)

    def test_should_name_the_red_base_of_a_catch_up(self):
        # Arrange
        self._record_checks(1)
        base_only = {resolve("integration/M4"): ProcessAnswer(stdout=f"{BASE_HEAD}\n")}

        # Act
        held_by = self._find(LOCAL_PROJECT, CATCH_UP, base_only)

        # Assert
        self.assertEqual(held_by.branch, "integration/M4")

    def test_should_name_the_red_main_branch_of_a_milestone_rebase(self):
        # Arrange
        self._record_checks(1)
        main_only = {resolve("main"): ProcessAnswer(stdout=f"{BASE_HEAD}\n")}

        # Act
        held_by = self._find(LOCAL_PROJECT, MILESTONE_REBASE, main_only)

        # Assert
        self.assertEqual(held_by.branch, "main")

    def test_should_name_the_base_of_the_forge_whose_check_run_is_pending(self):
        # Arrange
        base_of_the_forge = {resolve("origin/integration/M4"): ProcessAnswer(stdout=f"{BASE_HEAD}\n")}

        # Act
        held_by = self._find(GITHUB_PROJECT, CATCH_UP, base_of_the_forge, list_a_pending_check_run)

        # Assert
        self.assertEqual(
            held_by,
            HoldingHead(
                branch="integration/M4", proof=HeadProof(commit=BASE_HEAD, state="pending", failed_commands=())
            ),
        )
