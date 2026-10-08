import unittest

from brigade.system.scheduler_state import SchedulerState


class SchedulerStateTest(unittest.TestCase):
    def test_should_read_a_scheduler_installed_with_its_next_activation(self):
        # Arrange
        document = {
            "schema_version": 1,
            "installed": True,
            "unit_files": ["/units/brigade.timer"],
            "cron_line": "*/5 * * * * brigade tick --once",
            "next_activation": "2026-10-08T09:05:00Z",
        }

        # Act
        state = SchedulerState.from_document(document)

        # Assert
        self.assertEqual(
            state,
            SchedulerState(
                installed=True,
                unit_files=("/units/brigade.timer",),
                cron_line="*/5 * * * * brigade tick --once",
                next_activation="2026-10-08T09:05:00Z",
            ),
        )

    def test_should_read_a_scheduler_not_installed(self):
        # Arrange
        document = {
            "schema_version": 1,
            "installed": False,
            "unit_files": [],
            "cron_line": None,
            "next_activation": None,
        }

        # Act
        state = SchedulerState.from_document(document)

        # Assert
        self.assertEqual(state, SchedulerState(installed=False, unit_files=(), cron_line=None, next_activation=None))
