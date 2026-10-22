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
