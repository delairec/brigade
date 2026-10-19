import unittest

from brigade.adapters.schedulers.loop import install

NO_RUNTIME_NEEDED = None


class InstallLoopTest(unittest.TestCase):
    def test_should_install_nothing_and_name_the_command_to_keep_running(self):
        # Act
        installation = install({"brigade": "/opt/my brigade/bin/brigade"}, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            installation,
            {
                "schema_version": 1,
                "scheduler": "loop",
                "unit_files": [],
                "cron_line": None,
                "keep_running": "'/opt/my brigade/bin/brigade' tick --loop",
            },
        )
