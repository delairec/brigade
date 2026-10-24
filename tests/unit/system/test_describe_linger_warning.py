import unittest

from brigade.errors import ToolNotFound
from brigade.system.describe_linger_warning import describe_linger_warning
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


def _refuse_loginctl(request):
    raise ToolNotFound("loginctl is not on PATH")


class DescribeLingerWarningTest(unittest.TestCase):
    def test_should_warn_only_when_the_user_systemd_instance_does_not_linger(self):
        # Arrange
        rows = [
            ("Linger=yes\n", None),
            ("Linger=no\n", "no linger: the timer stops at logout; run loginctl enable-linger"),
        ]
        for linger, expected_warning in rows:
            with self.subTest(linger=linger):
                loginctl = RecordingProcessRunner(
                    {("loginctl", "show-user", "-p", "Linger"): ProcessAnswer(stdout=linger)}
                )

                # Act
                warning = describe_linger_warning(loginctl)

                # Assert
                self.assertEqual(warning, expected_warning)

    def test_should_warn_that_loginctl_is_not_on_the_path(self):
        # Act
        warning = describe_linger_warning(_refuse_loginctl)

        # Assert
        self.assertEqual(warning, "loginctl not on PATH")

    def test_should_warn_with_the_error_of_loginctl(self):
        # Arrange
        loginctl = RecordingProcessRunner(
            {
                ("loginctl", "show-user", "-p", "Linger"): ProcessAnswer(
                    exit_code=1, stderr="Failed to look up user : No such process\n"
                )
            }
        )

        # Act
        warning = describe_linger_warning(loginctl)

        # Assert
        self.assertEqual(warning, "loginctl show-user -p Linger exited 1: Failed to look up user : No such process")
