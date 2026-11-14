import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from brigade.tasks.push_task_branch import TaskPushDemand, push_task_branch
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_requests_opening_on import select_requests_opening_on

PASSING_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "c0ffee",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)
CHECK_OF_ANOTHER_COMMIT = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "bead",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)
FAILED_ACCEPTANCE_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "c0ffee", "checks": ['
    '{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []},'
    ' {"command": "coverage report", "passed": false, "duration_ms": 30, "tail": ["TOTAL 99%"]}]}'
)
GIT_PUSH = ("git", "push")


class PushTaskBranchTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout="/srv/oak-b12\n")
        self.processes.answer(("git", "branch", "--show-current"), stdout="feature/B12-the-parser\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"))}
        )
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", (("TITLE", "The parser"),))
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "refs/remotes/origin/feature/B12-the-parser"), stdout="bead\n"
        )
        self.processes.answer(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:bead",
                "origin",
                "feature/B12-the-parser",
            )
        )
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            WaveStarted(wave="oak_w1", project="oak", tasks=("B12",)),
        )

    def record_check(self, check: str) -> None:
        record = self.root / "state" / "checks" / "oak" / "B12.json"
        record.parent.mkdir(parents=True)
        record.write_text(check, encoding="utf-8")

    def create_demand(self) -> TaskPushDemand:
        return TaskPushDemand(path=Path("/srv/oak-b12"), task=None, environment={"GH_TOKEN": "t0ken"})

    def test_should_push_the_branch_of_the_task_with_the_lease_of_its_head_on_origin(self):
        # Arrange
        self.record_check(PASSING_CHECK)

        # Act
        push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertIn(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:bead",
                "origin",
                "feature/B12-the-parser",
            ),
            self.processes.list_argvs(),
        )

    def test_should_push_as_the_forge_account_of_the_build(self):
        # Arrange
        self.record_check(PASSING_CHECK)

        # Act
        push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(
            select_requests_opening_on(self.processes.requests, GIT_PUSH)[0].environment, {"GH_TOKEN": "t0ken"}
        )

    def test_should_report_the_branch_pushed_and_its_head(self):
        # Arrange
        self.record_check(PASSING_CHECK)

        # Act
        pushed = push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(
            pushed,
            {
                "schema_version": 1,
                "project": "oak",
                "task": "B12",
                "branch": "feature/B12-the-parser",
                "head": "c0ffee",
            },
        )

    def test_should_push_nothing_when_an_acceptance_command_of_the_build_failed(self):
        # Arrange
        self.record_check(FAILED_ACCEPTANCE_CHECK)

        # Act
        with self.assertRaises(BrigadeError):
            push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(select_requests_opening_on(self.processes.requests, GIT_PUSH), [])

    def test_should_name_the_acceptance_command_that_failed(self):
        # Arrange
        self.record_check(FAILED_ACCEPTANCE_CHECK)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(
            str(refusal.exception), "the last check of @TASK.B12 failed on coverage report; run brigade task check"
        )

    def test_should_push_nothing_when_no_check_of_the_task_is_recorded(self):
        # Act
        with self.assertRaises(BrigadeError):
            push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(select_requests_opening_on(self.processes.requests, GIT_PUSH), [])

    def test_should_push_nothing_when_the_last_check_is_of_another_commit_than_head(self):
        # Arrange
        self.record_check(CHECK_OF_ANOTHER_COMMIT)

        # Act
        with self.assertRaises(BrigadeError):
            push_task_branch(self.runtime, self.create_demand())

        # Assert
        self.assertEqual(select_requests_opening_on(self.processes.requests, GIT_PUSH), [])
