import os
import signal
import subprocess
import unittest

from brigade.system.stop_signal_receiver import StopRequested, StopSignalReceiver
from brigade.system.wait_within_limit import WallLimit, wait_within_limit
from tests.process_launcher import ProcessLauncher

NO_TIME = 0.0
ANY_GRACE_S = 30.0
SHORT_GRACE_S = 0.2
CUT = None
ANY_POLL_S = 2.0
SHORT_POLL_S = 0.05
LONG_LIMIT_S = 20.0


def _poll_nothing() -> None:
    pass


def _signal_itself() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


class WaitWithinLimitTestCase(unittest.TestCase):
    def start(self, argv: list, start_new_session: bool) -> subprocess.Popen:
        process = ProcessLauncher.start(argv, stdout=subprocess.PIPE, start_new_session=start_new_session)
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process


class WaitWithinLimitOfAProcessWithNoGroupTest(WaitWithinLimitTestCase):
    def test_should_cut_the_run_when_its_group_no_longer_exists(self):
        # Arrange
        process = self.start(["sleep", "0.5"], start_new_session=False)

        # Act
        exit_code = wait_within_limit(
            process, WallLimit(limit_s=NO_TIME, grace_before_kill_s=ANY_GRACE_S, poll_s=ANY_POLL_S), _poll_nothing
        )

        # Assert
        self.assertEqual(exit_code, CUT)


class WaitWithinLimitOfAProcessIgnoringTheStopSignalTest(WaitWithinLimitTestCase):
    def test_should_kill_the_group_once_the_grace_is_over(self):
        # Arrange
        process = self.start(["sh", "-c", 'trap "" TERM; echo ready; exec sleep 5'], start_new_session=True)
        process.stdout.readline()

        # Act
        exit_code = wait_within_limit(
            process, WallLimit(limit_s=NO_TIME, grace_before_kill_s=SHORT_GRACE_S, poll_s=ANY_POLL_S), _poll_nothing
        )

        # Assert
        self.assertEqual((exit_code, process.returncode), (CUT, -signal.SIGKILL))

    def test_should_kill_the_group_once_the_grace_is_over_when_the_run_is_stopped(self):
        # Arrange
        self.addCleanup(signal.signal, signal.SIGTERM, signal.getsignal(signal.SIGTERM))
        self.addCleanup(signal.signal, signal.SIGINT, signal.getsignal(signal.SIGINT))
        process = self.start(["sh", "-c", 'trap "" TERM; echo ready; exec sleep 5'], start_new_session=True)
        process.stdout.readline()
        limit = WallLimit(limit_s=LONG_LIMIT_S, grace_before_kill_s=SHORT_GRACE_S, poll_s=SHORT_POLL_S)

        # Act
        with StopSignalReceiver() as receiver, receiver.raising(), self.assertRaises(StopRequested):
            wait_within_limit(process, limit, _signal_itself)

        # Assert
        self.assertEqual(process.returncode, -signal.SIGKILL)


class WaitWithinLimitOfAProcessThatRunsForSeveralPollsTest(WaitWithinLimitTestCase):
    def test_should_poll_while_the_process_runs_then_answer_its_exit_code(self):
        # Arrange
        process = self.start(["sh", "-c", "sleep 0.5; exit 3"], start_new_session=True)
        polls = []

        # Act
        exit_code = wait_within_limit(
            process,
            WallLimit(limit_s=LONG_LIMIT_S, grace_before_kill_s=ANY_GRACE_S, poll_s=SHORT_POLL_S),
            lambda: polls.append("poll"),
        )

        # Assert
        self.assertEqual(exit_code, 3)
        self.assertGreaterEqual(len(polls), 2)


class PollFailure(Exception):
    pass


def _fail_to_poll() -> None:
    raise PollFailure("the journal could not be read")


class WaitWithinLimitOfAProcessWhosePollFailsTest(WaitWithinLimitTestCase):
    def test_should_stop_the_group_before_the_failure_leaves_the_wait(self):
        # Arrange
        process = self.start(["sleep", "5"], start_new_session=True)

        # Act
        with self.assertRaises(PollFailure):
            wait_within_limit(
                process,
                WallLimit(limit_s=LONG_LIMIT_S, grace_before_kill_s=SHORT_GRACE_S, poll_s=SHORT_POLL_S),
                _fail_to_poll,
            )

        # Assert
        self.assertEqual(process.returncode, -signal.SIGTERM)
