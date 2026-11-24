import json
import tempfile
import unittest
from pathlib import Path

from brigade.checks.promotion import check
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

HARBOUR_COVERS_TIDES = {"name": "COVERS", "atoms": ['"tides"'], "fields": []}
TASK_AT_THE_BASE = {
    "fields": [
        {"name": "STATUS", "atoms": ["todo"], "fields": []},
        {"name": "REFERENCE", "atoms": ['"artifact/harbour/index.html"'], "fields": [HARBOUR_COVERS_TIDES]},
    ]
}
TASK_REVISING_ITS_OWN_REFERENCE_AT_THE_HEAD = {
    "fields": [
        {"name": "STATUS", "atoms": ["implemented"], "fields": []},
        {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
        {
            "name": "REFERENCE",
            "atoms": ['"artifact/harbour/index.html"'],
            "fields": [
                {"name": "REVISES", "atoms": ['"the task draws the harbour page itself"'], "fields": []},
                HARBOUR_COVERS_TIDES,
            ],
        },
    ]
}


class PromotionCheckTest(unittest.TestCase):
    def test_should_judge_the_task_at_the_base_tree_of_its_pull_request_against_the_files_it_changes(self):
        # Arrange
        checkout = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (checkout / "artifact" / "harbour").mkdir(parents=True)
        (checkout / "artifact" / "harbour" / "index.html").write_text("<section id=tides></section>\n")
        subject = {
            "schema_version": 1,
            "project": "/srv/shop",
            "parameters": {"pr": "160"},
            "collected": {
                "pull-request": {
                    "summary": {
                        "base_tree": "/cache/shop/0f0f0f0",
                        "head_tree": "/cache/shop/1a2b3c4",
                        "checkout": str(checkout),
                        "task": "B1",
                        "pr": 160,
                        "changed": [{"path": "artifact/harbour/index.html", "insertions": 2, "deletions": 1}],
                    }
                }
            },
        }
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", "/cache/shop/1a2b3c4"): ProcessAnswer(
                    stdout=json.dumps(TASK_REVISING_ITS_OWN_REFERENCE_AT_THE_HEAD)
                ),
                ("awawa", "show", "@TASK.B1", "--json", "/cache/shop/0f0f0f0"): ProcessAnswer(
                    stdout=json.dumps(TASK_AT_THE_BASE)
                ),
            }
        )

        # Act
        document = check(subject, create_test_runtime(run_process=awawa))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "promotion",
                "result": "fail",
                "findings": [
                    (
                        "artifact/harbour/index.html is the REFERENCE @TASK.B1 is judged against, and its branch changes"
                        " it: a task delivering its reference says so with REVISES at the base of its branch"
                    ),
                    (
                        "the branch of @TASK.B1 adds or changes the REVISES or the READ under its REFERENCE"
                        " artifact/harbour/index.html, COVERS tides: the builder never does, the planner writes them"
                        " at ratification"
                    ),
                ],
            },
        )
