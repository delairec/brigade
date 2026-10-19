import os
import signal
import subprocess
import sys
import unittest

from brigade.system.is_catching_signal import is_catching_signal
from brigade.system.stop_signal_receiver import StopSignalReceiver
from tests.process_launcher import ProcessLauncher

PROCESS_CATCHING_ANOTHER_SIGNAL = """
import signal
signal.signal(signal.SIGUSR1, lambda _received, _frame: None)
print("caught", flush=True)
signal.pause()
"""


class IsCatchingSignalOfAProcessHoldingAStopSignalReceiverTest(unittest.TestCase):
    def test_should_read_the_stop_signal_caught(self):
        # Arrange
        self.enterContext(StopSignalReceiver())

        # Act
        catching = is_catching_signal(os.getpid(), signal.SIGTERM)

        # Assert
        self.assertTrue(catching)


class IsCatchingSignalOfAProcessCatchingAnotherSignalTest(unittest.TestCase):
    def test_should_read_the_stop_signal_left_to_its_default_action(self):
        # Arrange
        process = ProcessLauncher.start(
            [sys.executable, "-c", PROCESS_CATCHING_ANOTHER_SIGNAL], stdout=subprocess.PIPE, text=True
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        process.stdout.readline()

        # Act
        catching = is_catching_signal(process.pid, signal.SIGTERM)

        # Assert
        self.assertFalse(catching)


class IsCatchingSignalOfAProcessGoneTest(unittest.TestCase):
    def test_should_read_no_signal_caught_by_a_pid_no_process_holds(self):
        # Arrange
        gone = ProcessLauncher.start(["true"])
        gone.wait()

        # Act
        catching = is_catching_signal(gone.pid, signal.SIGTERM)

        # Assert
        self.assertFalse(catching)
