import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"
SYSTEMD_USER_MANAGER = str(EXECUTABLES / "systemd-user-manager")
SYSTEMD_OFFLINE = str(EXECUTABLES / "systemd-offline")
CRONTAB = str(EXECUTABLES / "crontab")
CRONTAB_FAILING = str(EXECUTABLES / "crontab-failing")

SYSTEMD_CONFIGURED = 'scheduler = "systemd"\n'
CRON_CONFIGURED = 'scheduler = "cron"\n'
LOOP_CONFIGURED = 'scheduler = "loop"\n'
NO_SCHEDULER_CONFIGURED = 'client = "claude-code"\n'
UNRELATED_CRON_LINE = "0 3 * * * backup"
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
        self.create_machine(Path(self.root.name).resolve())

    def tearDown(self):
        self.root.cleanup()

    def create_machine(self, root: Path) -> None:
        self.machine = TemporaryMachine(root)
        self.units = self.machine.config_home / "systemd" / "user"
        self.service = self.units / "brigade.service"
        self.timer = self.units / "brigade.timer"
        self.crontab = self.machine.home / "crontab"
        self.systemctl_calls = self.machine.home / "systemctl.calls"
        self.log = self.machine.state_home / "brigade" / "tick.log"

    def run_scheduler(self, path_directories: list, *arguments: str):
        environment = {**self.machine.describe_environment(), "PATH": os.pathsep.join(path_directories)}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "scheduler", *arguments, environment=environment)

    def describe_cron_line(self, search_path: str) -> str:
        return (
            f"*/5 * * * * mkdir -p {self.log.parent} && PATH={search_path}"
            f" XDG_CONFIG_HOME={self.machine.config_home} XDG_STATE_HOME={self.machine.state_home}"
            f" XDG_CACHE_HOME={self.machine.cache_home} {CLONE_ENTRY_POINT} tick --once"
            f" >/dev/null 2>>{self.log} # brigade scheduler install"
        )

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


class BrigadeSchedulerInstallWithSystemdConfigured(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(SYSTEMD_CONFIGURED)

    def test_should_write_the_service_running_the_installing_brigade_with_the_install_environment(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.service.read_text(), self.describe_service_unit(SYSTEMD_USER_MANAGER))

    def test_should_write_the_timer_firing_every_five_minutes_and_catching_up_a_missed_tick(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.timer.read_text(), TIMER_UNIT)

    def test_should_reload_the_user_manager_and_enable_the_timer_now(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.systemctl_calls.read_text(), "--user daemon-reload\n--user enable --now brigade.timer\n")

    def test_should_report_the_units_installed_in_the_versioned_document(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "systemd",
                "chosen_by": "configuration",
                "unit_files": [str(self.service), str(self.timer)],
                "cron_line": None,
                "keep_running": None,
            },
        )

    def test_should_print_the_units_installed_as_text(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            ["systemd installed, chosen by config.toml", f"unit  {self.service}", f"unit  {self.timer}"],
        )

    def test_should_leave_one_pair_of_units_when_run_twice(self):
        # Arrange
        self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.units.iterdir()), ["brigade.service", "brigade.timer"])


class BrigadeSchedulerInstallWithCronConfigured(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(CRON_CONFIGURED)
        self.crontab.write_text(f"{UNRELATED_CRON_LINE}\n")

    def test_should_append_the_tick_line_to_the_crontab(self):
        # Act
        completed = self.run_scheduler([CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.crontab.read_text(), f"{UNRELATED_CRON_LINE}\n{self.describe_cron_line(CRONTAB)}\n")

    def test_should_leave_one_tick_line_when_run_twice(self):
        # Arrange
        self.run_scheduler([CRONTAB], "install")

        # Act
        completed = self.run_scheduler([CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.crontab.read_text(), f"{UNRELATED_CRON_LINE}\n{self.describe_cron_line(CRONTAB)}\n")

    def test_should_report_the_cron_line_in_the_versioned_document(self):
        # Act
        completed = self.run_scheduler([CRONTAB], "install", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "cron",
                "chosen_by": "configuration",
                "unit_files": [],
                "cron_line": self.describe_cron_line(CRONTAB),
                "keep_running": None,
            },
        )

    def test_should_print_the_cron_line_as_text(self):
        # Act
        completed = self.run_scheduler([CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            ["cron installed, chosen by config.toml", f"cron line  {self.describe_cron_line(CRONTAB)}"],
        )


class BrigadeSchedulerInstallWithCronConfiguredOnAnEmptyCrontab(SchedulerTestCase):
    def test_should_write_the_tick_line_alone(self):
        # Arrange
        self.machine.write_configuration(CRON_CONFIGURED)

        # Act
        completed = self.run_scheduler([CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.crontab.read_text(), f"{self.describe_cron_line(CRONTAB)}\n")


class BrigadeSchedulerInstallWithTheLoopConfigured(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(LOOP_CONFIGURED)

    def test_should_install_nothing_and_name_the_command_to_keep_running(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "install", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "loop",
                "chosen_by": "configuration",
                "unit_files": [],
                "cron_line": None,
                "keep_running": f"{CLONE_ENTRY_POINT} tick --loop",
            },
        )
        self.assertEqual(
            (self.units.exists(), self.crontab.exists(), self.systemctl_calls.exists()), (False, False, False)
        )

    def test_should_print_the_command_to_keep_running_as_text(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "loop chosen by config.toml: nothing installed; keep this command running",
                f"{CLONE_ENTRY_POINT} tick --loop",
            ],
        )


class BrigadeSchedulerInstallWithoutTheSchedulerKey(SchedulerTestCase):
    def test_should_choose_systemd_where_the_user_instance_runs_else_cron(self):
        rows = [
            ("a running user instance", [SYSTEMD_USER_MANAGER, CRONTAB], "running", "systemd"),
            ("a degraded user instance", [SYSTEMD_USER_MANAGER, CRONTAB], "degraded", "systemd"),
            ("an offline user instance", [SYSTEMD_USER_MANAGER, CRONTAB], "offline", "cron"),
            ("no systemctl", [CRONTAB], "running", "cron"),
        ]
        self.machine.write_configuration(NO_SCHEDULER_CONFIGURED)
        for machine, path_directories, systemd_state, expected_scheduler in rows:
            with self.subTest(machine=machine):
                # Arrange
                (self.machine.home / "systemd-state").write_text(f"{systemd_state}\n")

                # Act
                completed = self.run_scheduler(path_directories, "install", "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                document = json.loads(completed.stdout)
                self.assertEqual((document["scheduler"], document["chosen_by"]), (expected_scheduler, "probe"))

    def test_should_say_the_probe_chose_it_in_the_text(self):
        # Arrange
        self.machine.write_configuration(NO_SCHEDULER_CONFIGURED)

        # Act
        completed = self.run_scheduler([SYSTEMD_OFFLINE, CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines()[0], "cron installed, chosen by the probe of the user systemd instance"
        )


class BrigadeSchedulerInstallOnAMachineWhosePathsHoldASpaceAndAPercentSign(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        machine_root = Path(self.root.name).resolve() / "a 100% b"
        machine_root.mkdir()
        self.create_machine(machine_root)

    def test_should_escape_them_in_the_service_unit(self):
        # Arrange
        self.machine.write_configuration(SYSTEMD_CONFIGURED)

        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        environment_lines = [line for line in self.service.read_text().splitlines() if line.startswith("Environment=")]
        root = Path(self.root.name).resolve()
        self.assertEqual(
            environment_lines[1:],
            [
                f'Environment="XDG_CONFIG_HOME={root}/a 100%% b/config"',
                f'Environment="XDG_STATE_HOME={root}/a 100%% b/state"',
                f'Environment="XDG_CACHE_HOME={root}/a 100%% b/cache"',
            ],
        )

    def test_should_quote_them_in_the_cron_line(self):
        # Arrange
        self.machine.write_configuration(CRON_CONFIGURED)

        # Act
        completed = self.run_scheduler([CRONTAB], "install")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        root = Path(self.root.name).resolve()
        self.assertEqual(
            self.crontab.read_text(),
            f"*/5 * * * * mkdir -p '{root}/a 100\\% b/state/brigade' && PATH={CRONTAB}"
            f" XDG_CONFIG_HOME='{root}/a 100\\% b/config' XDG_STATE_HOME='{root}/a 100\\% b/state'"
            f" XDG_CACHE_HOME='{root}/a 100\\% b/cache' {CLONE_ENTRY_POINT} tick --once"
            f" >/dev/null 2>>'{root}/a 100\\% b/state/brigade/tick.log' # brigade scheduler install\n",
        )


class BrigadeSchedulerInstallWhenTheConfigurationNamesAnUnknownScheduler(SchedulerTestCase):
    def test_should_exit_1_naming_the_scheduler(self):
        rows = [
            ('scheduler = "launchd"\n', "brigade scheduler install: no scheduler plugin launchd\n"),
            ('scheduler = "data"\n', "brigade scheduler install: no scheduler plugin data\n"),
            ('scheduler = "__init__"\n', "brigade scheduler install: no scheduler plugin __init__\n"),
        ]
        for configuration, expected_stderr in rows:
            with self.subTest(configuration=configuration):
                # Arrange
                self.machine.write_configuration(configuration)

                # Act
                completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "install")

                # Assert
                self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (1, "", expected_stderr))


class BrigadeSchedulerInstallWhenCrontabCannotBeListed(SchedulerTestCase):
    def test_should_exit_1_naming_the_crontab_failure(self):
        # Arrange
        self.machine.write_configuration(CRON_CONFIGURED)

        # Act
        completed = self.run_scheduler([CRONTAB_FAILING], "install")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade scheduler install: crontab -l exited 1: crontab: cannot open the spool directory\n"),
        )


class BrigadeSchedulerInstallBeforeInit(SchedulerTestCase):
    def test_should_install_the_scheduler_the_probe_chooses(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_OFFLINE, CRONTAB], "install", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "cron",
                "chosen_by": "probe",
                "unit_files": [],
                "cron_line": self.describe_cron_line(f"{SYSTEMD_OFFLINE}:{CRONTAB}"),
                "keep_running": None,
            },
        )


class BrigadeSchedulerStatusWhenNothingIsInstalled(SchedulerTestCase):
    def test_should_report_none_and_no_tick_yet_and_exit_0(self):
        rows = [("every tool", [SYSTEMD_USER_MANAGER, CRONTAB]), ("no tool", [])]
        for machine, path_directories in rows:
            with self.subTest(machine=machine):
                # Act
                completed = self.run_scheduler(path_directories, "status", "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout),
                    {
                        "schema_version": 1,
                        "scheduler": "none",
                        "unit_files": [],
                        "cron_line": None,
                        "next_activation": None,
                        "last_tick": None,
                    },
                )

    def test_should_print_none_and_never_as_text(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.splitlines(), ["scheduler  none", "last tick  never"])


class BrigadeSchedulerStatusWithSystemdInstalled(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(SYSTEMD_CONFIGURED)
        self.run_scheduler([SYSTEMD_USER_MANAGER], "install")
        heartbeat = self.machine.state_home / "brigade" / "tick.json"
        heartbeat.parent.mkdir(parents=True)
        heartbeat.write_text(LAST_TICK)

    def test_should_report_the_units_the_next_activation_and_the_last_tick(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "systemd",
                "unit_files": [str(self.service), str(self.timer)],
                "cron_line": None,
                "next_activation": NEXT_ACTIVATION,
                "last_tick": {"ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0},
            },
        )

    def test_should_report_no_next_activation_when_systemctl_is_missing(self):
        # Act
        completed = self.run_scheduler([CRONTAB], "status", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(json.loads(completed.stdout)["next_activation"])

    def test_should_print_the_status_as_text(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "scheduler  systemd",
                f"unit       {self.service}",
                f"unit       {self.timer}",
                f"next       {NEXT_ACTIVATION}",
                "last tick  2026-10-06T12:00:00Z, 0 actions applied in 4 ms",
            ],
        )


class BrigadeSchedulerStatusWithCronInstalled(SchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(CRON_CONFIGURED)
        self.crontab.write_text(f"{UNRELATED_CRON_LINE}\n")
        self.run_scheduler([CRONTAB], "install")

    def test_should_report_the_cron_line(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "scheduler": "cron",
                "unit_files": [],
                "cron_line": self.describe_cron_line(CRONTAB),
                "next_activation": None,
                "last_tick": None,
            },
        )

    def test_should_print_the_cron_line_as_text(self):
        # Act
        completed = self.run_scheduler([SYSTEMD_USER_MANAGER, CRONTAB], "status")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            ["scheduler  cron", f"cron line  {self.describe_cron_line(CRONTAB)}", "last tick  never"],
        )
