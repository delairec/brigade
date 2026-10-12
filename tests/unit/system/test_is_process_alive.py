import os
import unittest

from brigade.system.is_process_alive import is_process_alive

PROCESS_OF_ANOTHER_USER = 1
PID_HELD_BY_NO_PROCESS = 2**31 - 1


class IsProcessAliveTest(unittest.TestCase):
    def test_should_find_a_process_of_its_own_user_alive(self):
        # Arrange
        own_process = os.getpid()

        # Act
        alive = is_process_alive(own_process)

        # Assert
        self.assertTrue(alive)

    @unittest.skipIf(os.geteuid() == 0, "root may signal every process")
    def test_should_find_a_process_of_another_user_alive(self):
        # Act
        alive = is_process_alive(PROCESS_OF_ANOTHER_USER)

        # Assert
        self.assertTrue(alive)

    def test_should_find_a_pid_held_by_no_process_dead(self):
        # Act
        alive = is_process_alive(PID_HELD_BY_NO_PROCESS)

        # Assert
        self.assertFalse(alive)
