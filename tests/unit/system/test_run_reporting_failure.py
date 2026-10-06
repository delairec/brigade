import contextlib
import io
import unittest
from collections.abc import Callable

from brigade.errors import BrigadeError
from brigade.system.run_reporting_failure import run_reporting_failure


def run_capturing_stderr(action: Callable[[], None]) -> str:
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        run_reporting_failure(action, "tick")
    return stderr.getvalue()


def refuse_the_state_directory() -> None:
    raise BrigadeError("cannot write /srv/state/brigade: Permission denied")


def break_the_planner() -> None:
    raise RuntimeError("the planner broke")


class RunReportingFailureTest(unittest.TestCase):
    def test_should_run_the_action_and_report_nothing_when_it_succeeds(self):
        # Arrange
        calls = []

        # Act
        stderr = run_capturing_stderr(lambda: calls.append("ran"))

        # Assert
        self.assertEqual((calls, stderr), (["ran"], ""))

    def test_should_report_a_brigade_error_in_one_line_named_after_the_command(self):
        # Act
        stderr = run_capturing_stderr(refuse_the_state_directory)

        # Assert
        self.assertEqual(stderr, "brigade tick: cannot write /srv/state/brigade: Permission denied\n")

    def test_should_report_an_unexpected_exception_with_its_traceback(self):
        # Act
        stderr = run_capturing_stderr(break_the_planner)

        # Assert
        self.assertRegex(stderr, r"^Traceback \(most recent call last\):\n[\s\S]*\nRuntimeError: the planner broke\n$")
