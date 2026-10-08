import unittest

from brigade.system.scheduler_installation import SchedulerInstallation


class SchedulerInstallationTest(unittest.TestCase):
    def test_should_read_an_installation_of_cron(self):
        # Arrange
        document = {
            "schema_version": 1,
            "scheduler": "cron",
            "unit_files": [],
            "cron_line": "*/5 * * * * brigade tick --once",
            "keep_running": None,
        }

        # Act
        installation = SchedulerInstallation.from_document(document)

        # Assert
        self.assertEqual(
            installation,
            SchedulerInstallation(
                scheduler="cron", unit_files=(), cron_line="*/5 * * * * brigade tick --once", keep_running=None
            ),
        )

    def test_should_read_a_scheduler_that_installs_nothing(self):
        # Arrange
        document = {
            "schema_version": 1,
            "scheduler": "loop",
            "unit_files": ["/units/brigade.timer"],
            "cron_line": None,
            "keep_running": "brigade tick --loop",
        }

        # Act
        installation = SchedulerInstallation.from_document(document)

        # Assert
        self.assertEqual(
            installation,
            SchedulerInstallation(
                scheduler="loop",
                unit_files=("/units/brigade.timer",),
                cron_line=None,
                keep_running="brigade tick --loop",
            ),
        )
