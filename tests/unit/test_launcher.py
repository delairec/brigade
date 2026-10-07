import contextlib
import io
import unittest
from unittest import mock

from brigade.launcher import launch


class LaunchWhenThePythonFloorIsBreachedTest(unittest.TestCase):
    def test_should_refuse_and_exit_1(self):
        # Arrange
        stderr = io.StringIO()

        # Act
        with (
            mock.patch("brigade.launcher.describe_python_floor_breach", return_value="Python 3.11 required"),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            launch()

        # Assert
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(stderr.getvalue(), "Python 3.11 required\n")
