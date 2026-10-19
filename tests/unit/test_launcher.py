import contextlib
import io
import sys
import unittest
from unittest import mock

from brigade import VERSION
from brigade.launcher import launch


class LaunchTest(unittest.TestCase):
    def test_should_exit_on_the_code_of_the_command_line_it_was_given(self):
        # Arrange
        stdout = io.StringIO()

        # Act
        with (
            mock.patch.object(sys, "argv", ["brigade", "--version"]),
            contextlib.redirect_stdout(stdout),
            self.assertRaises(SystemExit) as exit_,
        ):
            launch()

        # Assert
        self.assertEqual((exit_.exception.code, stdout.getvalue()), (0, f"brigade {VERSION}\n"))
