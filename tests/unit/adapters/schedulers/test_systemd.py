import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.adapters.schedulers.systemd import install, read_status
from brigade.errors import ToolNotFound
from brigade.system.run_process import ProcessRecord


def create_runtime(exit_code: int, stdout: str) -> SimpleNamespace:
    def run_systemctl(request):
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=0
        )

    return SimpleNamespace(run_process=run_systemctl)


class ReadStatusOfAnInstalledTimerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.units = Path(self.root.name) / "systemd" / "user"
        self.units.mkdir(parents=True)
        (self.units / "brigade.service").write_text("[Service]\n")
        (self.units / "brigade.timer").write_text("[Timer]\n")

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_no_next_activation_when_systemctl_names_none(self):
        # Arrange
        rows = [
            ("systemctl failing", 1, "Failed to connect to bus\n"),
            ("an empty answer", 0, "\n"),
            ("no elapse planned", 0, "n/a\n"),
        ]
        for answer, exit_code, stdout in rows:
            with self.subTest(answer=answer):
                # Arrange
                runtime = create_runtime(exit_code, stdout)

                # Act
                status = read_status({"unit_directory": str(self.units)}, runtime)

                # Assert
                self.assertEqual(
                    status,
                    {
                        "schema_version": 1,
                        "installed": True,
                        "unit_files": [str(self.units / "brigade.service"), str(self.units / "brigade.timer")],
                        "cron_line": None,
                        "next_activation": None,
                    },
                )


class ReadStatusOfANextActivationTest(ReadStatusOfAnInstalledTimerTest):
    def test_should_read_the_next_activation_systemctl_names(self):
        # Arrange
        runtime = create_runtime(0, "Mon 2026-10-19 09:05:00 CEST\n")

        # Act
        status = read_status({"unit_directory": str(self.units)}, runtime)

        # Assert
        self.assertEqual(status["next_activation"], "Mon 2026-10-19 09:05:00 CEST")

    def test_should_read_no_next_activation_without_systemctl(self):
        # Arrange
        def refuse_missing_systemctl(request):
            raise ToolNotFound("systemctl is not on PATH")

        # Act
        status = read_status({"unit_directory": str(self.units)}, SimpleNamespace(run_process=refuse_missing_systemctl))

        # Assert
        self.assertIsNone(status["next_activation"])


class InstallSystemdTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.units = Path(self.root.name) / "systemd" / "user"
        self.commands = []

    def run_systemctl(self, request):
        self.commands.append(request.argv)
        return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout="", stderr="", duration_ms=0)

    def test_should_write_the_units_escaping_their_values_and_enable_the_timer(self):
        # Arrange
        request = {
            "unit_directory": str(self.units),
            "brigade": '/opt/my "brigade"/bin/brigade$',
            "environment": {"BRIGADE_NOTE": "100%"},
        }

        # Act
        installation = install(request, SimpleNamespace(run_process=self.run_systemctl))

        # Assert
        service = (self.units / "brigade.service").read_text()
        self.assertEqual(
            (
                installation,
                'Environment="BRIGADE_NOTE=100%%"' in service,
                '/opt/my \\"brigade\\"/bin/brigade$$' in service,
                self.commands,
            ),
            (
                {
                    "schema_version": 1,
                    "scheduler": "systemd",
                    "unit_files": [str(self.units / "brigade.service"), str(self.units / "brigade.timer")],
                    "cron_line": None,
                    "keep_running": None,
                },
                True,
                True,
                [("systemctl", "--user", "daemon-reload"), ("systemctl", "--user", "enable", "--now", "brigade.timer")],
            ),
        )
