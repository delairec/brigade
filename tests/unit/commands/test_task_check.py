import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.task_check import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime

THE_TASK_OF_THE_BRANCH = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}
PASSED_CHECK = {"command": "python3 -m unittest", "passed": True, "duration_ms": 1200, "tail": []}
FAILED_CHECK = {
    "command": "awawa lint --strict .",
    "passed": False,
    "duration_ms": 300,
    "tail": ["L025 a mention in prose", "1 finding"],
}


class TaskCheckTextTest(unittest.TestCase):
    def test_should_print_each_verdict_then_the_tail_of_each_failure(self):
        # Arrange
        document = {"checks": [PASSED_CHECK, FAILED_CHECK]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "pass  python3 -m unittest  1.2 s\n"
            "fail  awawa lint --strict .  0.3 s\n"
            "\n"
            "$ awawa lint --strict .\n"
            "L025 a mention in prose\n"
            "1 finding",
        )


class TaskCheckExitCodeTest(unittest.TestCase):
    def test_should_fail_when_one_check_fails(self):
        # Arrange
        rows = [("every check passed", [PASSED_CHECK], 0), ("one check failed", [PASSED_CHECK, FAILED_CHECK], 1)]
        for case, checks, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code({"checks": checks})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class TaskCheckRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(task=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class TaskCheckOutsideATaskTest(unittest.TestCase):
    def test_should_refuse_a_branch_that_is_not_the_branch_of_a_task(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_runtime(root, run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a task/<slug>/<task> branch")
