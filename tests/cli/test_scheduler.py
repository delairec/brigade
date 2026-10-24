import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"
SYSTEMD_USER_MANAGER = str(EXECUTABLES / "systemd-user-manager")
CRONTAB = str(EXECUTABLES / "crontab")

SYSTEMD_CONFIGURED = 'scheduler = "systemd"\n'
NEXT_ACTIVATION = "Tue 2026-10-06 12:05:00 UTC"
LAST_TICK = '{"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0}'
TIMER_UNIT = (
    "[Unit]\n"
    "Description=brigade tick every five minutes\n"
    "\n"
    "[Timer]\n"
    "OnCalendar=*:0/5\n"
    "Persistent=true\n"
    "\n"
    "[Install]\n"
    "WantedBy=timers.target\n"
)


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.units = self.machine.config_home / "systemd" / "user"
        self.service = self.units / "brigade.service"
        self.timer = self.units / "brigade.timer"

    def tearDown(self):
        self.root.cleanup()

    def run_scheduler(self, path_directories: list, *arguments: str):
        environment = {**self.machine.describe_environment(), "PATH": os.pathsep.join(path_directories)}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "scheduler", *arguments, environment=environment)

    def describe_service_unit(self, search_path: str) -> str:
        return (
            "[Unit]\n"
            "Description=brigade tick\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            f'Environment="PATH={search_path}"\n'
            f'Environment="XDG_CONFIG_HOME={self.machine.config_home}"\n'
            f'Environment="XDG_STATE_HOME={self.machine.state_home}"\n'
            f'Environment="XDG_CACHE_HOME={self.machine.cache_home}"\n'
            f'ExecStart="{CLONE_ENTRY_POINT}" tick --once\n'
        )


class BrigadeSchedulerInstallWithSystemdConfiguredTest(SchedulerTestCase):
    def test_should_write_the_units_running_the_installing_brigade_and_enable_the_timer(self):
        # Arrange
        self.machine.write_configuration(SYSTEMD_CONFIGURED)

        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "systemd installed, chosen by config.toml",
                f"unit  {self.service}",
                f"unit  {self.timer}",
                "warning  no linger: the timer stops at logout; run loginctl enable-linger",
            ],
        )
        self.assertEqual(completed.stderr, "")
        self.assertEqual(self.service.read_text(), self.describe_service_unit(SYSTEMD_USER_MANAGER))
        self.assertEqual(self.timer.read_text(), TIMER_UNIT)
        self.assertEqual(
            (self.machine.home / "systemctl.calls").read_text(),
            "--user daemon-reload\n--user enable --now brigade.timer\n",
        )


class BrigadeSchedulerStatusWithSystemdInstalledTest(SchedulerTestCase):
    def test_should_print_the_units_the_next_activation_and_the_stale_last_tick(self):
        # Arrange
        self.units.mkdir(parents=True)
        self.service.write_text(self.describe_service_unit(SYSTEMD_USER_MANAGER))
        self.timer.write_text(TIMER_UNIT)
        heartbeat = self.machine.state_home / "brigade" / "tick.json"
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.write_text(LAST_TICK)

        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "scheduler  systemd",
                f"unit       {self.service}",
                f"unit       {self.timer}",
                f"next       {NEXT_ACTIVATION}",
                "last tick  2026-10-06T12:00:00Z, 0 actions applied in 4 ms",
                "stale      the last tick is older than 15 minutes",
            ],
        )
        self.assertEqual(completed.stderr, "")
