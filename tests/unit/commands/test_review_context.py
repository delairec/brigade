import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.review_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TASK_WORKTREE, TIDEPOOL_PROJECT, WAVE_STARTED
from tests.unit.verify.test_record_verdict import ForgeDouble

VERDICT_FINDING = {"id": "1", "grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}
CHANGES_REQUESTED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "changes_requested",
    "reason": "body: the body keeps the placeholder $checks",
}


def create_document(request: str | None) -> dict:
    return {
        "schema_version": 1,
        "project": "tidepool",
        "pr": 42,
        "task": "T7",
        "head": "8885daa",
        "request": request,
        "review": "verdict",
        "findings": [VERDICT_FINDING],
    }


class ReviewContextTextTest(unittest.TestCase):
    def test_should_print_the_head_the_request_and_each_finding_under_its_identifier(self):
        # Arrange
        document = create_document("body: the body keeps the placeholder $checks")

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# head\n8885daa\n\n"
            "# request\nbody: the body keeps the placeholder $checks\n\n"
            "# review\nverdict\n\n"
            "# findings\n## 1\ngrade: high\nfile: src/tides.py\nline: 12\nbroken: SPEC 2 of @TASK.T7",
        )

    def test_should_leave_the_request_out_when_no_preflight_sent_the_task_back(self):
        # Arrange
        no_request = None

        # Act
        text = COMMAND.render_text(create_document(no_request))

        # Assert
        self.assertNotIn("# request", text)


class ReviewContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(pr=42)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class ReviewContextExitCodeTest(unittest.TestCase):
    def test_should_exit_0(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document(None))

        # Assert
        self.assertEqual(exit_code, 0)


class ReviewContextOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED, CHANGES_REQUESTED])
        self.runtime = create_runtime(
            self.root,
            run_process=create_machine_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}, "POLICY": {}}, TASK_WORKTREE),
            resolve_plugin=lambda kind, name, **places: ForgeDouble(),
        )

    def test_should_give_the_context_of_the_review_of_the_task_of_the_pull_request(self):
        # Act
        document = COMMAND.run(SimpleNamespace(pr=42), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "tidepool",
                "pr": 42,
                "task": "T7",
                "head": "8885daa",
                "request": "body: the body keeps the placeholder $checks",
                "review": "verdict",
                "findings": [],
            },
        )

    def test_should_refuse_a_pull_request_no_task_opened(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(pr=41), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")
