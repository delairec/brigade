import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.review_reply import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TASK_WORKTREE, TIDEPOOL_PROJECT, WAVE_STARTED
from tests.unit.review.test_assemble_review_context import VERDICT_CHANGES
from tests.unit.review.test_record_review_answers import ReplyingForgeDouble


def create_document(login: str | None) -> dict:
    return {
        "schema_version": 1,
        "project": "tidepool",
        "wave": "tidepool_w16",
        "task": "T7",
        "pr": 42,
        "head": "8885daa",
        "answers": [{"finding": "1", "answer": "fixed by 8885daa"}],
        "login": login,
    }


class ReviewReplyTextTest(unittest.TestCase):
    def test_should_name_the_answers_recorded(self):
        # Arrange
        no_login = None

        # Act
        text = COMMAND.render_text(create_document(no_login))

        # Assert
        self.assertEqual(text, "findings answered on #42, @TASK.T7 at 8885daa: 1")

    def test_should_name_the_login_the_replies_were_posted_as(self):
        # Act
        text = COMMAND.render_text(create_document("tidepool-remediate"))

        # Assert
        self.assertEqual(text, "findings answered on #42, @TASK.T7 at 8885daa: 1, posted as tidepool-remediate")


class ReviewReplyRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42, file="answers.json")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class ReviewReplyExitCodeTest(unittest.TestCase):
    def test_should_exit_0(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document(None))

        # Assert
        self.assertEqual(exit_code, 0)


class ReviewReplyOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED, VERDICT_CHANGES])
        self.runtime = create_runtime(
            self.root,
            run_process=create_machine_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}, "POLICY": {}}, TASK_WORKTREE),
            resolve_plugin=lambda kind, name, **places: ReplyingForgeDouble(),
        )
        self.answers_file = self.root / "answers.json"

    def test_should_record_the_answers_the_file_holds(self):
        # Arrange
        self.answers_file.write_text(json.dumps({"answers": [{"finding": "1", "answer": "fixed by 8885daa"}]}))

        # Act
        document = COMMAND.run(Namespace(pr=42, file=str(self.answers_file)), self.runtime)

        # Assert
        self.assertEqual(document["answers"], [{"finding": "1", "answer": "fixed by 8885daa"}])

    def test_should_refuse_a_file_holding_no_json_document(self):
        # Arrange
        self.answers_file.write_text("fixed")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            COMMAND.run(Namespace(pr=42, file=str(self.answers_file)), self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), f"the answers file {self.answers_file} holds no JSON document")

    def test_should_refuse_a_file_it_cannot_read(self):
        # Arrange
        missing_file = self.root / "missing.json"

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            COMMAND.run(Namespace(pr=42, file=str(missing_file)), self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot read {missing_file}: No such file or directory")
