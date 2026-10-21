import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.scheduler_status import COMMAND
from tests.unit.commands.command_runtime import create_runtime, write_ledger

NOT_INSTALLED = {"schema_version": 1, "installed": False, "unit_files": [], "cron_line": None, "next_activation": None}
CRON_INSTALLED = {
    "schema_version": 1,
    "installed": True,
    "unit_files": [],
    "cron_line": "*/5 * * * * brigade tick --once",
    "next_activation": None,
}

NOTHING_PAUSED = []
NOTHING_PARKED = []


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
                    "tick_stale_after": 15,
                    "stale": False,
                    "paused_waves": NOTHING_PAUSED,
                    "parked_tasks": NOTHING_PARKED,
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
                    "tick_stale_after": 15,
                    "stale": False,
                    "paused_waves": NOTHING_PAUSED,
                    "parked_tasks": NOTHING_PARKED,
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

    def test_should_print_why_the_tick_is_stale(self):
        # Arrange
        rows = [
            (
                "a last tick too old",
                {"ts": "2026-10-19T08:40:00Z", "duration_ms": 120, "actions_applied": 2},
                (
                    "scheduler  cron\ncron line  */5 * * * * b\n"
                    "last tick  2026-10-19T08:40:00Z, 2 actions applied in 120 ms\n"
                    "stale      the last tick is older than 15 minutes"
                ),
            ),
            (
                "no tick since the install",
                None,
                (
                    "scheduler  cron\ncron line  */5 * * * * b\nlast tick  never\n"
                    "stale      no tick ran while a scheduler is installed"
                ),
            ),
        ]
        for case, last_tick, expected_text in rows:
            with self.subTest(case=case):
                # Arrange
                document = {
                    "schema_version": 1,
                    "scheduler": "cron",
                    "unit_files": [],
                    "cron_line": "*/5 * * * * b",
                    "next_activation": None,
                    "last_tick": last_tick,
                    "tick_stale_after": 15,
                    "stale": True,
                    "paused_waves": NOTHING_PAUSED,
                    "parked_tasks": NOTHING_PARKED,
                }

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected_text)

    def test_should_print_the_paused_waves_and_the_parked_tasks(self):
        # Arrange
        document = {
            "schema_version": 1,
            "scheduler": "none",
            "unit_files": [],
            "cron_line": None,
            "next_activation": None,
            "last_tick": None,
            "tick_stale_after": 15,
            "stale": False,
            "paused_waves": [
                {"wave": "brigade_w1", "reason": "quota", "resume_at": "2026-10-19T10:00:00Z"},
                {"wave": "brigade_w2", "reason": "forge_account", "resume_at": None},
            ],
            "parked_tasks": [{"task": "B12", "wave": "brigade_w1", "reason": "blocked"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            (
                "scheduler  none\nlast tick  never\n"
                "paused     brigade_w1, quota, resumes at 2026-10-19T10:00:00Z\n"
                "paused     brigade_w2, forge_account, resumes on brigade wave resume\n"
                "parked     B12 of brigade_w1, blocked"
            ),
        )


class SchedulerStatusExitCodeTest(unittest.TestCase):
    def test_should_fail_when_the_tick_is_stale(self):
        # Arrange
        rows = [("a fresh tick", False, 0), ("a stale tick", True, 1)]
        for case, stale, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code({"schema_version": 1, "stale": stale})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


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

    def write_heartbeat(self, ts: str) -> None:
        (self.root / "state").mkdir(exist_ok=True)
        (self.root / "state" / "tick.json").write_text(
            json.dumps({"schema_version": 1, "ts": ts, "duration_ms": 120, "actions_applied": 2}),
            encoding="utf-8",
        )

    def write_configuration(self, content: str) -> None:
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text(content, encoding="utf-8")

    def read_status(self, statuses: dict) -> dict:
        runtime = create_runtime(self.root, resolve_plugin=_create_scheduler_resolution(statuses))
        return COMMAND.run(SimpleNamespace(), runtime)

    def test_should_report_the_first_scheduler_installed_and_the_last_heartbeat(self):
        # Arrange
        self.write_heartbeat("2026-10-19T08:55:00Z")
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}

        # Act
        document = self.read_status(statuses)

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
                "tick_stale_after": 15,
                "stale": False,
                "paused_waves": [],
                "parked_tasks": [],
            },
        )

    def test_should_report_no_scheduler_when_none_is_installed(self):
        # Arrange
        statuses = {"systemd": NOT_INSTALLED, "cron": NOT_INSTALLED}

        # Act
        document = self.read_status(statuses)

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
                "tick_stale_after": 15,
                "stale": False,
                "paused_waves": [],
                "parked_tasks": [],
            },
        )

    def test_should_judge_the_last_tick_stale_once_older_than_15_minutes(self):
        # Arrange
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}
        rows = [
            ("five minutes old", "2026-10-19T08:55:00Z", False),
            ("fifteen minutes old", "2026-10-19T08:45:00Z", False),
            ("one second past fifteen minutes", "2026-10-19T08:44:59Z", True),
        ]
        for case, ts, expected_stale in rows:
            with self.subTest(case=case):
                # Arrange
                self.write_heartbeat(ts)

                # Act
                document = self.read_status(statuses)

                # Assert
                self.assertEqual(document["stale"], expected_stale)

    def test_should_judge_the_last_tick_stale_past_the_minutes_config_sets(self):
        # Arrange
        self.write_configuration("tick_stale_after = 5\n")
        self.write_heartbeat("2026-10-19T08:54:00Z")
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}

        # Act
        document = self.read_status(statuses)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "scheduler": "cron",
                "unit_files": [],
                "cron_line": "*/5 * * * * brigade tick --once",
                "next_activation": None,
                "last_tick": {"ts": "2026-10-19T08:54:00Z", "duration_ms": 120, "actions_applied": 2},
                "tick_stale_after": 5,
                "stale": True,
                "paused_waves": [],
                "parked_tasks": [],
            },
        )

    def test_should_judge_the_tick_stale_when_none_ran_while_a_scheduler_is_installed(self):
        # Arrange
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}

        # Act
        document = self.read_status(statuses)

        # Assert
        self.assertEqual(document["stale"], True)

    def test_should_summarise_the_paused_waves_and_the_parked_tasks_of_the_open_waves(self):
        # Arrange
        self.write_heartbeat("2026-10-19T08:55:00Z")
        write_ledger(
            self.root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T07:00:00Z",
                    "event": "wave.started",
                    "wave": "brigade_w1",
                    "project": "brigade",
                    "branch": "main",
                    "tasks": ["B12", "B13"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T07:01:00Z",
                    "event": "wave.started",
                    "wave": "brigade_w2",
                    "project": "brigade",
                    "branch": "main",
                    "tasks": ["B14"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T07:02:00Z",
                    "event": "wave.started",
                    "wave": "brigade_w3",
                    "project": "brigade",
                    "branch": "main",
                    "tasks": ["B15"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T07:03:00Z",
                    "event": "wave.started",
                    "wave": "brigade_w4",
                    "project": "brigade",
                    "branch": "main",
                    "tasks": ["B16"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:10:00Z",
                    "event": "task.parked",
                    "wave": "brigade_w1",
                    "task": "B12",
                    "reason": "blocked",
                    "blockers": ["@OPEN_QUESTION.Q1"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:11:00Z",
                    "event": "task.parked",
                    "wave": "brigade_w1",
                    "task": "B13",
                    "reason": "blocked",
                    "blockers": ["@OPEN_QUESTION.Q2"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:12:00Z",
                    "event": "task.state",
                    "wave": "brigade_w1",
                    "task": "B13",
                    "state": "running",
                    "reason": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:12:30Z",
                    "event": "task.state",
                    "wave": "brigade_w2",
                    "task": "B14",
                    "state": "parked",
                    "reason": "pull request closed",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:12:40Z",
                    "event": "task.state",
                    "wave": "brigade_w3",
                    "task": "B15",
                    "state": "parked",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:13:00Z",
                    "event": "task.parked",
                    "wave": "brigade_w4",
                    "task": "B16",
                    "reason": "blocked",
                    "blockers": ["@OPEN_QUESTION.Q3"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:14:00Z",
                    "event": "wave.cancelled",
                    "wave": "brigade_w4",
                    "reason": "the user cancelled it",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T08:00:00Z",
                    "event": "wave.paused",
                    "wave": "brigade_w1",
                    "reason": "quota",
                    "resume_at": "2026-10-19T10:00:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T08:01:00Z",
                    "event": "wave.paused",
                    "wave": "brigade_w2",
                    "reason": "forge_account",
                    "resume_at": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T08:02:00Z",
                    "event": "wave.paused",
                    "wave": "brigade_w3",
                    "reason": "quota",
                    "resume_at": "2026-10-19T08:30:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T08:30:00Z",
                    "event": "wave.resumed",
                    "wave": "brigade_w3",
                    "reason": "quota",
                },
            ],
        )
        statuses = {"systemd": NOT_INSTALLED, "cron": CRON_INSTALLED}

        # Act
        document = self.read_status(statuses)

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
                "tick_stale_after": 15,
                "stale": False,
                "paused_waves": [
                    {"wave": "brigade_w1", "reason": "quota", "resume_at": "2026-10-19T10:00:00Z"},
                    {"wave": "brigade_w2", "reason": "forge_account", "resume_at": None},
                ],
                "parked_tasks": [
                    {"task": "B12", "wave": "brigade_w1", "reason": "blocked"},
                    {"task": "B14", "wave": "brigade_w2", "reason": "pull request closed"},
                    {"task": "B15", "wave": "brigade_w3", "reason": None},
                ],
            },
        )
