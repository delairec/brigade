import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_review_answered import TaskReviewAnswered
from brigade.review.record_review_answers import AnswersDemand, record_review_answers
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import create_corpus_double, write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.review.test_assemble_review_context import (
    CHANGES_REQUESTED,
    OPENED,
    POLICY_UNDER_APPROVAL,
    VERDICT_CHANGES,
    ThreadListingForgeDouble,
)

NO_POLICY = {}
REMEDIATE_ACCOUNTS = Configuration(forge_accounts={"remediate": "tidepool-remediate"})


class ReplyingForgeDouble(ThreadListingForgeDouble):
    def reply_review_thread(self, request: dict, runtime) -> dict:
        self.questions.append(("reply_review_thread", request))
        return {"schema_version": 1}


class RecordReviewAnswersTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.forge = ReplyingForgeDouble()
        write_ledger(self.root, [CHANGES_REQUESTED, VERDICT_CHANGES])

    def record(self, policies: dict, answers: dict) -> dict:
        runtime = create_test_runtime(
            create_test_paths(self.root), run_process=create_corpus_double({"POLICY": policies})
        )
        return record_review_answers(
            runtime,
            AnswersDemand(
                opened=OPENED,
                project_path="/home/user/tidepool",
                answers=answers,
                forge=self.forge,
                configuration=REMEDIATE_ACCOUNTS,
            ),
        )

    def read_last_event(self) -> dict:
        return json.loads((self.root / "state" / "ledger" / "2026-10.jsonl").read_text().splitlines()[-1])

    def list_replies(self) -> list[dict]:
        return [request for operation, request in self.forge.questions if operation == "reply_review_thread"]


class RecordReviewAnswersUnderTheVerdictModeTest(RecordReviewAnswersTestCase):
    def test_should_record_the_answers_at_the_head_of_the_pull_request_without_a_login(self):
        # Arrange
        answers = {"answers": [{"finding": "1", "answer": "fixed by 8885daa"}]}

        # Act
        self.record(NO_POLICY, answers)

        # Assert
        self.assertEqual(
            self.read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.review_answered",
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "answers": [{"finding": "1", "answer": "fixed by 8885daa"}],
                "login": None,
            },
        )

    def test_should_record_answers_the_ledger_reads_back_as_the_answers_to_the_review(self):
        # Arrange
        answers = {"answers": [{"finding": "1", "answer": "fixed by 8885daa"}]}

        # Act
        self.record(NO_POLICY, answers)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[-1].event,
            TaskReviewAnswered(
                project="tidepool",
                wave="tidepool_w16",
                task="T7",
                pr=42,
                head="8885daa",
                answers=({"finding": "1", "answer": "fixed by 8885daa"},),
                login=None,
            ),
        )

    def test_should_post_no_reply(self):
        # Arrange
        answers = {"answers": [{"finding": "1", "answer": "fixed by 8885daa"}]}

        # Act
        self.record(NO_POLICY, answers)

        # Assert
        self.assertEqual(self.list_replies(), [])

    def test_should_refuse_answers_leaving_a_finding_unanswered_and_record_nothing(self):
        # Arrange
        no_answer = {"answers": []}

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.record(NO_POLICY, no_answer)

        # Assert
        self.assertEqual(str(refusal.exception), "the answers are refused: finding 1 has no answer")
        self.assertEqual(self.read_last_event()["event"], "task.verdict")


class RecordReviewAnswersUnderTheApprovalModeTest(RecordReviewAnswersTestCase):
    def test_should_reply_each_answer_on_its_thread_as_the_login_of_the_remediate_slot(self):
        # Arrange
        answers = {"answers": [{"finding": "PRRT_kwDOA1", "answer": "fixed by 8885daa"}]}

        # Act
        self.record(POLICY_UNDER_APPROVAL, answers)

        # Assert
        self.assertEqual(
            self.list_replies(),
            [
                {
                    "schema_version": 1,
                    "repository": "/home/user/tidepool",
                    "thread": "PRRT_kwDOA1",
                    "body": "fixed by 8885daa",
                    "environment": {"GH_TOKEN": "token-of-tidepool-remediate"},
                }
            ],
        )

    def test_should_record_the_login_the_replies_ran_as(self):
        # Arrange
        answers = {"answers": [{"finding": "PRRT_kwDOA1", "answer": "fixed by 8885daa"}]}

        # Act
        document = self.record(POLICY_UNDER_APPROVAL, answers)

        # Assert
        self.assertEqual(document["login"], "tidepool-review")
