import subprocess
import sys
import tempfile
import unittest

from tests.process_launcher import ProcessLauncher

PRINT_THE_WORKING_DIRECTORY_AND_ITS_INPUT = "import os, sys; print(os.getcwd(), sys.stdin.read())"


class ProcessLauncherRunTest(unittest.TestCase):
    def test_should_complete_the_command_in_the_directory_and_with_the_input_its_caller_gives(self):
        # Arrange
        directory = self.enterContext(tempfile.TemporaryDirectory())

        # Act
        completed = ProcessLauncher.run(
            [sys.executable, "-c", PRINT_THE_WORKING_DIRECTORY_AND_ITS_INPUT],
            cwd=directory,
            input="request",
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, f"{directory} request\n")

    def test_should_raise_on_a_failed_command_whose_caller_asks_for_the_check(self):
        # Act
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            ProcessLauncher.run([sys.executable, "-c", "raise SystemExit(3)"], check=True)

        # Assert
        self.assertEqual(raised.exception.returncode, 3)


class ProcessLauncherStartTest(unittest.TestCase):
    def test_should_hand_the_running_command_to_its_caller(self):
        # Act
        output = ProcessLauncher.start(
            [sys.executable, "-c", "print('started')"], stdout=subprocess.PIPE, text=True
        ).communicate()

        # Assert
        self.assertEqual(output, ("started\n", None))
