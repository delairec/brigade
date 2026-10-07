import contextlib
import io
import sys
import unittest
from unittest import mock

from brigade.launcher import launch

PYTHON_BELOW_THE_FLOOR = (3, 10, 14)


class LaunchUnderAPythonBelowTheFloorTest(unittest.TestCase):
    def test_should_exit_1_naming_the_python_it_needs(self):
        # Arrange
        stderr = io.StringIO()

        # Act
        with (
            mock.patch.object(sys, "version_info", PYTHON_BELOW_THE_FLOOR),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as exit_,
        ):
            launch()

        # Assert
        self.assertEqual(
            (exit_.exception.code, stderr.getvalue()),
            (1, "brigade needs Python 3.11 or later; this is Python 3.10.14\n"),
        )
