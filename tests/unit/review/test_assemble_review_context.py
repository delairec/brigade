import tempfile
import unittest
from pathlib import Path

from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.review.assemble_review_context import ReviewDemand, assemble_review_context
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_ledger
from tests.unit.verify.test_record_verdict import ForgeDouble

OPENED = TaskPrOpened(
    project="tidepool", task="T7", wave="tidepool_w16", branch="task/M4-tides/T7", pr=42, login="tidepool-bot"
)
NO_POLICY = {}
POLICY_UNDER_APPROVAL = {"tidepool_policy": (("PROJECT", "@PROJECT.tidepool"), ("REVIEW", "approval"))}
CHANGES_REQUESTED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "changes_requested",
    "reason": "body: the body keeps the placeholder $checks",
}
VERDICT_CHANGES = {
    "schema_version": 1,
    "ts": "2026-10-18T13:00:00Z",
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


class ThreadListingForgeDouble(ForgeDouble):
    def list_review_threads(self, request: dict, runtime) -> dict:
        self.questions.append(("list_review_threads", request))
        return {
            "schema_version": 1,
            "threads": [
                {
                    "id": "PRRT_kwDOA1",
                    "file": "src/tides.py",
                    "line": 12,
                    "author": "octo-reviewer",
                    "body": "the tide table is read twice",
                }
            ],
        }


def create_demand(forge) -> ReviewDemand:
    return ReviewDemand(opened=OPENED, project_path="/home/user/tidepool", forge=forge, environment={"GH_TOKEN": "t"})


class AssembleReviewContextUnderTheVerdictModeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_give_the_head_the_request_and_the_findings_of_the_last_verdict_each_by_its_identifier(self):
        # Arrange
        write_ledger(self.root, [CHANGES_REQUESTED, VERDICT_CHANGES])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": NO_POLICY}))
        demand = ReviewDemand(
            opened=OPENED, project_path="/home/user/tidepool", forge=ForgeDouble(), environment={"GH_TOKEN": "t"}
        )

        # Act
        context = assemble_review_context(runtime, demand)

        # Assert
        self.assertEqual(
            context,
            {
                "project": "tidepool",
                "pr": 42,
                "task": "T7",
                "head": "8885daa",
                "request": "body: the body keeps the placeholder $checks",
                "review": "verdict",
                "findings": [
                    {"id": "1", "grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}
                ],
            },
        )

    def test_should_give_no_finding_to_a_task_no_verdict_judged(self):
        # Arrange
        write_ledger(self.root, [CHANGES_REQUESTED])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": NO_POLICY}))

        # Act
        context = assemble_review_context(runtime, create_demand(ForgeDouble()))

        # Assert
        self.assertEqual(context["findings"], [])

    def test_should_give_the_request_of_the_last_sending_back(self):
        # Arrange
        changes_requested_again = {
            "schema_version": 1,
            "ts": "2026-10-18T14:00:00Z",
            "event": "task.state",
            "wave": "tidepool_w16",
            "task": "T7",
            "state": "changes_requested",
            "reason": "body: the body names no task",
        }
        write_ledger(self.root, [CHANGES_REQUESTED, changes_requested_again])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": NO_POLICY}))

        # Act
        context = assemble_review_context(runtime, create_demand(ForgeDouble()))

        # Assert
        self.assertEqual(context["request"], "body: the body names no task")

    def test_should_keep_the_request_through_the_repair_round_that_follows_it(self):
        # Arrange
        fixing = {
            "schema_version": 1,
            "ts": "2026-10-18T14:00:00Z",
            "event": "task.state",
            "wave": "tidepool_w16",
            "task": "T7",
            "state": "fixing",
        }
        write_ledger(self.root, [CHANGES_REQUESTED, fixing])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": NO_POLICY}))

        # Act
        context = assemble_review_context(runtime, create_demand(ForgeDouble()))

        # Assert
        self.assertEqual(context["request"], "body: the body keeps the placeholder $checks")

    def test_should_give_no_request_to_a_task_no_preflight_sent_back(self):
        # Arrange
        write_ledger(self.root, [VERDICT_CHANGES])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": NO_POLICY}))

        # Act
        context = assemble_review_context(runtime, create_demand(ForgeDouble()))

        # Assert
        self.assertIsNone(context["request"])


class AssembleReviewContextUnderTheApprovalModeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_give_the_open_review_threads_each_by_its_thread_identifier(self):
        # Arrange
        write_ledger(self.root, [CHANGES_REQUESTED, VERDICT_CHANGES])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": POLICY_UNDER_APPROVAL}))

        # Act
        context = assemble_review_context(runtime, create_demand(ThreadListingForgeDouble()))

        # Assert
        self.assertEqual(
            context["findings"],
            [
                {
                    "id": "PRRT_kwDOA1",
                    "file": "src/tides.py",
                    "line": 12,
                    "author": "octo-reviewer",
                    "body": "the tide table is read twice",
                }
            ],
        )

    def test_should_ask_the_forge_for_the_threads_of_the_pull_request_as_the_login_of_the_environment(self):
        # Arrange
        write_ledger(self.root, [CHANGES_REQUESTED])
        runtime = create_runtime(self.root, run_process=create_corpus_double({"POLICY": POLICY_UNDER_APPROVAL}))
        forge = ThreadListingForgeDouble()

        # Act
        assemble_review_context(runtime, create_demand(forge))

        # Assert
        self.assertIn(
            (
                "list_review_threads",
                {
                    "schema_version": 1,
                    "repository": "/home/user/tidepool",
                    "number": 42,
                    "environment": {"GH_TOKEN": "t"},
                },
            ),
            forge.questions,
        )
