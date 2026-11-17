import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.build_check import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, write_ledger
from tests.unit.commands.test_preflight import WAVE_STARTED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

THE_TASK_OF_THE_BRANCH = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/srv/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}
TASK_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/srv/tidepool-T7\n",
    ("git", "branch", "--show-current"): "feature/T7-tides\n",
    ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): "/srv/tidepool/.git\n",
    ("git", "status", "--porcelain"): " M src/tide.py\0",
}
TIDEPOOL = {"PROJECT": {"tidepool": (("PATH", "/srv/tidepool"), ("MAIN", "main"))}, "TASK": {"T7": ()}}
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
            "ok  python3 -m unittest  1.2 s\n"
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
        runtime = create_test_runtime(
            create_test_paths(root), run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT)
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a <prefix>/<task>-<slug> branch")


class TaskCheckOfATaskWorktreeTest(unittest.TestCase):
    def test_should_refuse_a_worktree_holding_changes_head_does_not(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(root, [WAVE_STARTED])
        runtime = create_test_runtime(
            create_test_paths(root), run_process=create_machine_double(TIDEPOOL, TASK_BRANCH_CHECKOUT)
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "the worktree of @TASK.T7 holds changes HEAD does not: src/tide.py; commit them, then run brigade build check",
        )
