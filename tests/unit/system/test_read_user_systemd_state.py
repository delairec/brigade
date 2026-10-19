import unittest

from brigade.system.read_user_systemd_state import read_user_systemd_state
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadUserSystemdStateTest(unittest.TestCase):
    def test_should_answer_the_first_line_systemctl_prints_whatever_it_exits(self):
        # Arrange
        systemctl = RecordingProcessRunner(
            {
                ("systemctl", "--user", "is-system-running"): ProcessAnswer(
                    exit_code=1, stdout="degraded\nunits failed\n"
                )
            }
        )

        # Act
        state = read_user_systemd_state(systemctl)

        # Assert
        self.assertEqual(state, "degraded")
