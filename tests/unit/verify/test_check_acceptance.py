import unittest
from pathlib import Path

from brigade.verify.check_acceptance import AcceptanceFacts, check_acceptance
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

HEAD_TREE = Path("/cache/shop/2222222")


class CheckAcceptanceTest(unittest.TestCase):
    def test_should_pass_naming_each_command_with_its_exit_code(self):
        # Arrange
        facts = AcceptanceFacts(head_tree=HEAD_TREE, commands=("python3 -m unittest", "ruff check ."))

        # Act
        check = check_acceptance(RecordingProcessRunner(), facts)

        # Assert
        self.assertEqual(
            check,
            {
                "name": "acceptance",
                "verdict": "pass",
                "findings": [],
                "commands": [
                    {"command": "python3 -m unittest", "exit_code": 0},
                    {"command": "ruff check .", "exit_code": 0},
                ],
            },
        )

    def test_should_fail_naming_the_failing_command_and_its_output(self):
        # Arrange
        runner = RecordingProcessRunner(
            {("ruff", "check", "."): ProcessAnswer(exit_code=1, stdout="brigade/cli.py:3:1: F401\n")}
        )
        facts = AcceptanceFacts(head_tree=HEAD_TREE, commands=("python3 -m unittest", "ruff check ."))

        # Act
        check = check_acceptance(runner, facts)

        # Assert
        self.assertEqual(
            check,
            {
                "name": "acceptance",
                "verdict": "fail",
                "findings": ["ruff check . exited 1", "brigade/cli.py:3:1: F401"],
                "commands": [
                    {"command": "python3 -m unittest", "exit_code": 0},
                    {"command": "ruff check .", "exit_code": 1},
                ],
            },
        )

    def test_should_run_each_command_in_the_tree_of_the_head(self):
        # Arrange
        runner = RecordingProcessRunner()
        facts = AcceptanceFacts(head_tree=HEAD_TREE, commands=("python3 -m unittest",))

        # Act
        check_acceptance(runner, facts)

        # Assert
        self.assertEqual(
            [(request.argv, request.cwd) for request in runner.requests],
            [(("python3", "-m", "unittest"), "/cache/shop/2222222")],
        )
