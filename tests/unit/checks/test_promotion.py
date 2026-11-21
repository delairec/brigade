import json
import unittest

from brigade.checks.promotion import check
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

TASK_CITING_THE_HARBOUR = {
    "fields": [
        {"name": "STATUS", "atoms": ["implemented"], "fields": []},
        {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
        {
            "name": "REFERENCE",
            "atoms": ['"artifact/harbour/index.html"'],
            "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
        },
    ]
}


class PromotionCheckTest(unittest.TestCase):
    def test_should_judge_the_task_against_the_files_its_pull_request_changes(self):
        # Arrange
        subject = {
            "schema_version": 1,
            "project": "/srv/shop",
            "parameters": {"pr": "160"},
            "collected": {
                "pull-request": {
                    "summary": {
                        "base_tree": "/cache/shop/0f0f0f0",
                        "head_tree": "/cache/shop/1a2b3c4",
                        "checkout": "/srv/shop",
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
                    stdout=json.dumps(TASK_CITING_THE_HARBOUR)
                ),
                ("awawa", "show", "@TASK.B1", "--json", "/cache/shop/0f0f0f0"): ProcessAnswer(
                    stdout=json.dumps(TASK_CITING_THE_HARBOUR)
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
                    )
                ],
            },
        )
