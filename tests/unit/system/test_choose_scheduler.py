import unittest

from brigade.errors import ToolNotFound
from brigade.system.choose_scheduler import SchedulerChoice, choose_scheduler
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.refuse_to_run import refuse_to_run

NO_SCHEDULER_CONFIGURED = None


def _refuse_systemctl(request):
    raise ToolNotFound("systemctl is not on PATH")


class ChooseSchedulerTest(unittest.TestCase):
    def test_should_choose_the_scheduler_the_configuration_names_without_probing(self):
        # Act
        choice = choose_scheduler("cron", refuse_to_run)

        # Assert
        self.assertEqual(choice, SchedulerChoice(name="cron", chosen_by="configuration"))

    def test_should_choose_by_the_probe_of_the_user_systemd_instance_without_a_configured_scheduler(self):
        # Arrange
        rows = [
            ("a running instance", "running\n", "systemd"),
            ("a degraded instance", "degraded\n", "systemd"),
            ("an offline instance", "offline\n", "cron"),
        ]
        for case, state, expected_name in rows:
            with self.subTest(case=case):
                systemctl = RecordingProcessRunner(
                    {("systemctl", "--user", "is-system-running"): ProcessAnswer(stdout=state)}
                )

                # Act
                choice = choose_scheduler(NO_SCHEDULER_CONFIGURED, systemctl)

                # Assert
                self.assertEqual(choice, SchedulerChoice(name=expected_name, chosen_by="probe"))

    def test_should_choose_cron_when_systemctl_is_not_on_the_path(self):
        # Act
        choice = choose_scheduler(NO_SCHEDULER_CONFIGURED, _refuse_systemctl)

        # Assert
        self.assertEqual(choice, SchedulerChoice(name="cron", chosen_by="probe"))
