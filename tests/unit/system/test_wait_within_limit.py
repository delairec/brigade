import subprocess
import unittest
from unittest import mock

from brigade.system.wait_within_limit import wait_within_limit


class WaitWithinLimitTest(unittest.TestCase):
    def test_should_return_the_exit_code_when_the_process_finishes_in_time(self):
        # Arrange
        process = mock.Mock(spec=subprocess.Popen)
        process.wait.return_value = 0

        # Act
        result = wait_within_limit(process, 5.0)

        # Assert
        self.assertEqual(result, 0)

    def test_should_return_none_when_the_process_is_killed_after_the_limit(self):
        # Arrange
        process = mock.Mock(spec=subprocess.Popen)
        process.pid = 12345
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=0.01),
            subprocess.TimeoutExpired(cmd="test", timeout=30.0),
            0,
        ]

        # Act
        with mock.patch("os.killpg") as killpg:
            result = wait_within_limit(process, 0.01)

        # Assert
        self.assertIsNone(result)
        self.assertEqual(killpg.call_count, 2)

    def test_should_ignore_a_process_lookup_error_when_signalling(self):
        # Arrange
        process = mock.Mock(spec=subprocess.Popen)
        process.pid = 12345
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=0.01),
            0,
        ]

        # Act
        with mock.patch("os.killpg", side_effect=ProcessLookupError):
            result = wait_within_limit(process, 0.01)

        # Assert
        self.assertIsNone(result)
