import signal
import subprocess
import unittest
from unittest import mock

from brigade.system import wait_within_limit as wait_module
from brigade.system.wait_within_limit import wait_within_limit

NO_TIME = 0.0
SHORT_GRACE_S = 0.2
CUT = None


class WaitWithinLimitTestCase(unittest.TestCase):
    def start(self, argv: list, start_new_session: bool) -> subprocess.Popen:
        process = subprocess.Popen(  # noqa: S603 - the test's own command line
            argv, stdout=subprocess.PIPE, start_new_session=start_new_session
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process


class WaitWithinLimitOfAProcessWithNoGroupTest(WaitWithinLimitTestCase):
    def test_should_cut_the_run_when_its_group_no_longer_exists(self):
        # Arrange
        process = self.start(["sleep", "0.5"], start_new_session=False)

        # Act
        exit_code = wait_within_limit(process, NO_TIME)

        # Assert
        self.assertEqual(exit_code, CUT)


class WaitWithinLimitOfAProcessIgnoringTheStopSignalTest(WaitWithinLimitTestCase):
    def test_should_kill_the_group_once_the_grace_is_over(self):
        # Arrange
        process = self.start(["sh", "-c", 'trap "" TERM; echo ready; exec sleep 30'], start_new_session=True)
        process.stdout.readline()

        # Act
        with mock.patch.object(wait_module, "GRACE_BEFORE_KILL_S", SHORT_GRACE_S):
            exit_code = wait_within_limit(process, NO_TIME)

        # Assert
        self.assertEqual((exit_code, process.returncode), (CUT, -signal.SIGKILL))
