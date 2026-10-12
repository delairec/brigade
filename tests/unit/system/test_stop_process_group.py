import signal
import subprocess
import unittest

from brigade.system.stop_process_group import stop_process_group

SHORT_GRACE_S = 0.2
ANY_GRACE_S = 30.0


class StopProcessGroupTestCase(unittest.TestCase):
    def start(self, argv: list, start_new_session: bool) -> subprocess.Popen:
        process = subprocess.Popen(  # noqa: S603 - the test's own command line
            argv, stdout=subprocess.PIPE, start_new_session=start_new_session
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process


class StopProcessGroupOfAProcessThatEndsOnTheStopSignalTest(StopProcessGroupTestCase):
    def test_should_end_the_process_on_the_stop_signal(self):
        # Arrange
        process = self.start(["sleep", "5"], start_new_session=True)

        # Act
        stop_process_group(process, ANY_GRACE_S)

        # Assert
        self.assertEqual(process.returncode, -signal.SIGTERM)


class StopProcessGroupOfAProcessIgnoringTheStopSignalTest(StopProcessGroupTestCase):
    def test_should_kill_the_group_once_the_grace_is_over(self):
        # Arrange
        process = self.start(["sh", "-c", 'trap "" TERM; echo ready; exec sleep 5'], start_new_session=True)
        process.stdout.readline()

        # Act
        stop_process_group(process, SHORT_GRACE_S)

        # Assert
        self.assertEqual(process.returncode, -signal.SIGKILL)


class StopProcessGroupOfAProcessWithNoGroupTest(StopProcessGroupTestCase):
    def test_should_wait_for_the_process_when_its_group_no_longer_exists(self):
        # Arrange
        process = self.start(["true"], start_new_session=False)
        process.wait()

        # Act
        stop_process_group(process, ANY_GRACE_S)

        # Assert
        self.assertEqual(process.returncode, 0)
