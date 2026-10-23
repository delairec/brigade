import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.system.parse_configuration import Configuration
from brigade.verify.record_verdict import VerdictDemand, record_verdict
from tests.unit.commands.command_runtime import create_corpus_double

TIDEPOOL = "tidepool"
OPENED = TaskPrOpened(
    project=TIDEPOOL, task="T7", wave="tidepool_w16", branch="task/M4-tides/T7", pr=42, login="tidepool-bot"
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

BROKEN_SPEC = {"grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}
CHANGES = {"head": "8885daa", "verdict": "changes", "findings": [BROKEN_SPEC]}
REVIEW_ACCOUNTS = Configuration(forge_accounts={"review": "tidepool-review"})
POLICY_UNDER_APPROVAL = {"tidepool_policy": (("PROJECT", "@PROJECT.tidepool"), ("REVIEW", "approval"))}


class ForgeDouble:
    def __init__(self):
        self.questions = []

    def read_pull_request(self, request: dict, runtime) -> dict:
        self.questions.append(("read_pull_request", request))
        return {
            "schema_version": 1,
            "pull_request": {
                "number": 42,
                "title": "feat(tides): read the tides (@TASK.T7)",
                "body": "Read the tides\n",
                "head": "task/M4-tides/T7",
                "head_sha": "8885daa",
                "checks": [],
            },
        }

    def read_login_environment(self, request: dict, runtime) -> dict:
        self.questions.append(("read_login_environment", request))
        return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}

    def describe_account(self, request: dict, runtime) -> dict:
        self.questions.append(("describe_account", request))
        return {"schema_version": 1, "login": "tidepool-review"}

    def post_review(self, request: dict, runtime) -> dict:
        self.questions.append(("post_review", request))
        return {"schema_version": 1}


class RecordVerdictTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.forge = ForgeDouble()

    def record(self, policies: dict, verdict: dict) -> dict:
        runtime = create_test_runtime(
            create_test_paths(self.root), run_process=create_corpus_double({"POLICY": policies})
        )
        return record_verdict(
            runtime,
            VerdictDemand(
                project_path="/home/user/tidepool",
                opened=OPENED,
                verdict=verdict,
                forge=self.forge,
                configuration=REVIEW_ACCOUNTS,
            ),
        )

    def read_ledger(self) -> list[dict]:
        return [
            json.loads(line) for line in (self.root / "state" / "ledger" / "2026-10.jsonl").read_text().splitlines()
        ]

    def list_posted_reviews(self) -> list[dict]:
        return [request for operation, request in self.forge.questions if operation == "post_review"]


class RecordVerdictUnderTheVerdictModeTest(RecordVerdictTestCase):
    def test_should_record_the_verdict_on_the_head_of_the_pull_request_without_a_login(self):
        # Arrange
        no_policy = {}

        # Act
        self.record(no_policy, CHANGES)

        # Assert
        self.assertEqual(
            self.read_ledger(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.verdict",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "verdict": "changes",
                    "findings": [{"grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}],
                    "login": None,
                }
            ],
        )

    def test_should_post_no_review(self):
        # Arrange
        no_policy = {}

        # Act
        self.record(no_policy, CHANGES)

        # Assert
        self.assertEqual(self.list_posted_reviews(), [])

    def test_should_give_the_recorded_event(self):
        # Arrange
        no_policy = {}

        # Act
        document = self.record(no_policy, {"head": "8885daa", "verdict": "pass", "findings": []})

        # Assert
        self.assertEqual(
            document,
            {
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "verdict": "pass",
                "findings": [],
                "login": None,
            },
        )


class RecordVerdictUnderTheApprovalModeTest(RecordVerdictTestCase):
    def test_should_post_a_review_requesting_changes_under_the_login_of_the_review_slot(self):
        # Act
        self.record(POLICY_UNDER_APPROVAL, CHANGES)

        # Assert
        self.assertEqual(
            self.list_posted_reviews(),
            [
                {
                    "schema_version": 1,
                    "repository": "/home/user/tidepool",
                    "number": 42,
                    "event": "request_changes",
                    "commit": "8885daa",
                    "body": "verdict changes\n- high src/tides.py:12: SPEC 2 of @TASK.T7\n",
                    "environment": {"GH_TOKEN": "token-of-tidepool-review"},
                }
            ],
        )

    def test_should_approve_on_a_pass(self):
        # Act
        self.record(POLICY_UNDER_APPROVAL, {"head": "8885daa", "verdict": "pass", "findings": []})

        # Assert
        self.assertEqual(self.list_posted_reviews()[0]["event"], "approve")

    def test_should_record_the_login_the_review_ran_as(self):
        # Act
        self.record(POLICY_UNDER_APPROVAL, CHANGES)

        # Assert
        self.assertEqual(self.read_ledger()[0]["login"], "tidepool-review")


class RecordVerdictOfAHeadNoLongerTheHeadTest(RecordVerdictTestCase):
    def setUp(self):
        super().setUp()
        self.judged_before_a_push = {"head": "fedcba9", "verdict": "pass", "findings": []}

    def test_should_refuse_the_verdict_naming_both_heads(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.record(POLICY_UNDER_APPROVAL, self.judged_before_a_push)

        # Assert
        self.assertEqual(str(raised.exception), "the verdict judged fedcba9, no longer the head of #42, now 8885daa")

    def test_should_record_nothing_and_post_no_review(self):
        # Act
        with self.assertRaises(BrigadeError):
            self.record(POLICY_UNDER_APPROVAL, self.judged_before_a_push)

        # Assert
        self.assertEqual(self.list_posted_reviews(), [])
        self.assertFalse((self.root / "state" / "ledger" / "2026-10.jsonl").exists())
