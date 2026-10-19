import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.scheduler_status import COMMAND
from tests.unit.commands.command_runtime import create_runtime

NOT_INSTALLED = {"schema_version": 1, "installed": False, "unit_files": [], "cron_line": None, "next_activation": None}
CRON_INSTALLED = {
    "schema_version": 1,
    "installed": True,
    "unit_files": [],
    "cron_line": "*/5 * * * * brigade tick --once",
    "next_activation": None,
}


class SchedulerDouble:
    def __init__(self, status: dict):
        self.status = status

    def read_status(self, request: dict, runtime) -> dict:
        return self.status


def _create_scheduler_resolution(statuses: dict):
    return lambda kind, name, **places: SchedulerDouble(statuses[name])


class SchedulerStatusTextTest(unittest.TestCase):
    def test_should_print_the_scheduler_and_the_last_tick(self):
        # Arrange
        rows = [
            (
                "a timer never fired",
                {
                    "scheduler": "systemd",
                    "unit_files": ["/u/brigade.timer"],
                    "cron_line": None,
                    "next_activation": "2026-10-19T09:05:00Z",
                    "last_tick": None,
                },
                "scheduler  systemd\nunit       /u/brigade.timer\nnext       2026-10-19T09:05:00Z\nlast tick  never",
            ),
            (
                "a cron line that fired",
                {
                    "scheduler": "cron",
                    "unit_files": [],
                    "cron_line": "*/5 * * * * b",
                    "next_activation": None,
                    "last_tick": {"ts": "2026-10-19T09:00:00Z", "duration_ms": 120, "actions_applied": 2},
                },
                (
                    "scheduler  cron\ncron line  */5 * * * * b\n"
                    "last tick  2026-10-19T09:00:00Z, 2 actions applied in 120 ms"
                ),
            ),
        ]
        for case, status, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text({"schema_version": 1, **status})

                # Assert
                self.assertEqual(text, expected_text)


class SchedulerStatusExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class SchedulerStatusRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class SchedulerStatusOfTheMachineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_report_the_first_scheduler_installed_and_the_last_heartbeat(self):
        # Arrange
        (self.root / "state").mkdir()
        (self.root / "state" / "tick.json").write_text(
            json.dumps({"schema_version": 1, "ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2}),
            encoding="utf-8",
        )
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}
        runtime = create_runtime(self.root, resolve_plugin=_create_scheduler_resolution(statuses))

        # Act
        document = COMMAND.run(SimpleNamespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "scheduler": "cron",
                "unit_files": [],
                "cron_line": "*/5 * * * * brigade tick --once",
                "next_activation": None,
                "last_tick": {"ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2},
            },
        )

    def test_should_report_no_scheduler_when_none_is_installed(self):
        # Arrange
        statuses = {"systemd": NOT_INSTALLED, "cron": NOT_INSTALLED}
        runtime = create_runtime(self.root, resolve_plugin=_create_scheduler_resolution(statuses))

        # Act
        document = COMMAND.run(SimpleNamespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "scheduler": "none",
                "unit_files": [],
                "cron_line": None,
                "next_activation": None,
                "last_tick": None,
            },
        )
