import tempfile
import unittest
from pathlib import Path

from brigade.adapters.schedulers.systemd import install, read_status
from brigade.errors import CannotWrite, ToolNotFound
from brigade.runtime import Runtime
from brigade.system.run_process import ProcessRecord
from tests.list_entry_names import list_entry_names
from tests.unit.create_test_runtime import create_test_runtime


def create_runtime(exit_code: int, stdout: str) -> Runtime:
    def run_systemctl(request):
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=0
        )

    return create_test_runtime(run_process=run_systemctl)


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
        status = read_status(
            {"unit_directory": str(self.units)}, create_test_runtime(run_process=refuse_missing_systemctl)
        )

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
        installation = install(request, create_test_runtime(run_process=self.run_systemctl))

        # Assert
        service = (self.units / "brigade.service").read_text()
        self.assertEqual(
            installation,
            {
                "schema_version": 1,
                "scheduler": "systemd",
                "unit_files": [str(self.units / "brigade.service"), str(self.units / "brigade.timer")],
                "cron_line": None,
                "keep_running": None,
            },
        )
        self.assertEqual('Environment="BRIGADE_NOTE=100%%"' in service, True)
        self.assertEqual('/opt/my \\"brigade\\"/bin/brigade$$' in service, True)
        self.assertEqual(
            self.commands,
            [("systemctl", "--user", "daemon-reload"), ("systemctl", "--user", "enable", "--now", "brigade.timer")],
        )

    def test_should_spare_the_runs_a_tick_detached_when_the_service_ends(self):
        # Arrange
        request = {"unit_directory": str(self.units), "brigade": "/opt/brigade/bin/brigade", "environment": {}}

        # Act
        install(request, create_test_runtime(run_process=self.run_systemctl))

        # Assert
        self.assertEqual("KillMode=process" in (self.units / "brigade.service").read_text().splitlines(), True)

    def test_should_leave_one_pair_of_units_when_installed_over_an_earlier_install(self):
        # Arrange
        request = {"unit_directory": str(self.units), "brigade": "/opt/brigade/bin/brigade", "environment": {}}
        install(request, create_test_runtime(run_process=self.run_systemctl))

        # Act
        install(request, create_test_runtime(run_process=self.run_systemctl))

        # Assert
        self.assertEqual(list_entry_names(self.units), ["brigade.service", "brigade.timer"])

    def test_should_refuse_naming_the_unit_directory_a_file_stands_for(self):
        # Arrange
        self.units.parent.mkdir(parents=True)
        self.units.write_text("")
        request = {"unit_directory": str(self.units), "brigade": "/opt/brigade/bin/brigade", "environment": {}}

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            install(request, create_test_runtime(run_process=self.run_systemctl))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.units}: File exists")

    def test_should_refuse_naming_the_unit_a_directory_stands_for(self):
        # Arrange
        rows = ["brigade.service", "brigade.timer"]
        for unit in rows:
            with self.subTest(unit=unit):
                # Arrange
                units = Path(self.root.name) / unit / "systemd" / "user"
                (units / unit).mkdir(parents=True)
                request = {"unit_directory": str(units), "brigade": "/opt/brigade/bin/brigade", "environment": {}}

                # Act
                with self.assertRaises(CannotWrite) as refusal:
                    install(request, create_test_runtime(run_process=self.run_systemctl))

                # Assert
                self.assertEqual(str(refusal.exception), f"cannot write {units / unit}: Is a directory")
