import os
import unittest
from pathlib import Path
from unittest import mock

from brigade.system.read_process_identity import read_process_identity

PID_HELD_BY_NO_PROCESS = 2**31 - 1


class ReadProcessIdentityTest(unittest.TestCase):
    def test_should_identify_a_living_process_by_its_start_time_and_the_boot_of_the_kernel(self):
        # Arrange
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()

        # Act
        identity = read_process_identity(os.getpid())

        # Assert
        self.assertRegex(identity, rf"^\d+ {boot_id}$")

    def test_should_identify_no_process_on_a_pid_no_process_holds(self):
        # Act
        identity = read_process_identity(PID_HELD_BY_NO_PROCESS)

        # Assert
        self.assertIsNone(identity)

    def test_should_identify_no_process_on_a_pid_whose_process_is_released_while_its_stat_is_read(self):
        # Arrange
        released_while_read = ProcessLookupError(3, "No such process")

        # Act
        with mock.patch.object(Path, "read_text", side_effect=released_while_read):
            identity = read_process_identity(os.getpid())

        # Assert
        self.assertIsNone(identity)
