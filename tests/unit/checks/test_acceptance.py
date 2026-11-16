import unittest

from brigade.checks.acceptance import check
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class AcceptanceCheckTest(unittest.TestCase):
    def test_should_run_the_acceptance_commands_of_the_project_in_the_checkout_of_the_head(self):
        # Arrange
        runner = RecordingProcessRunner({("python3", "-m", "unittest"): ProcessAnswer(stdout="FAILED\n", exit_code=1)})
        subject = {
            "schema_version": 1,
            "project": "/srv/shop",
            "parameters": {},
            "collected": {
                "pull-request": {
                    "summary": {"checkout": "/srv/cache/shop/2222222", "acceptance": [["python3", "-m", "unittest"]]}
                }
            },
        }

        # Act
        document = check(subject, create_test_runtime(run_process=runner))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "acceptance",
                "verdict": "fail",
                "findings": ["python3 -m unittest exited 1", "FAILED"],
                "commands": [
                    {"command": "python3 -m unittest", "exit_code": 1, "duration_ms": 0, "output": "FAILED\n"}
                ],
            },
        )

    def test_should_run_the_acceptance_commands_in_the_worktree_of_a_task(self):
        # Arrange
        runner = RecordingProcessRunner()
        subject = {
            "schema_version": 1,
            "project": "/srv/oak",
            "parameters": {"worktree": "/srv/oak-b12"},
            "collected": {
                "task-worktree": {
                    "summary": {"checkout": "/srv/oak-b12", "acceptance": [["python3", "-m", "unittest"]]}
                }
            },
        }

        # Act
        check(subject, create_test_runtime(run_process=runner))

        # Assert
        self.assertEqual(runner.commands, [("/srv/oak-b12", ("python3", "-m", "unittest"))])
