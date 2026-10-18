import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import ANY

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT
from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_tick import LaunchingTickTestCase, WaveTickTestCase

RATE_LIMITED_SESSION = "rate-limited-session"
RESET_AT_15 = {"hour": "15:00", "timezone": "UTC"}
NO_RESET = None
RESUMED_RESULT = {**DONE_RESULT, "session_id": None}
RUNNING_S3 = (
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "running"}\n'
)
PAUSED_ON_THE_QUOTA_UNTIL_THE_PAST = (
    '{"schema_version": 1, "ts": "2026-10-13T11:30:00Z", "event": "wave.paused", "wave": "shop_w1",'
    ' "reason": "quota", "resume_at": "2026-10-13T12:00:00Z"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:30:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "paused:quota"}\n'
)
FORGE_ACCOUNT_UNAVAILABLE = (
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "forge_account.unavailable",'
    ' "login": "octo-bot", "key": "build"}\n'
)
PAUSED_ON_THE_FORGE_ACCOUNT = (
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "wave.paused", "wave": "shop_w1",'
    ' "reason": "forge_account", "resume_at": null}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "wave.paused", "wave": "cafe_w1",'
    ' "reason": "quota", "resume_at": "2026-10-13T12:00:00Z"}\n'
)
RESUME_AT_15 = r"^\d{4}-\d{2}-\d{2}T15:00:00Z$"


class RateLimitedRunTestCase(LaunchingTickTestCase):
    client_operations = ""
    reset = RESET_AT_15

    def setUp(self):
        super().setUp()
        self.recordings = Path(self.root.name) / "recordings"
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{self.recordings}"\n'
            f'operations = "{self.client_operations}"\n{COUNTING_CLIENT}'
        )
        rate_limited = {
            **DONE_RESULT,
            "outcome": "failed",
            "session_id": RATE_LIMITED_SESSION,
            "error_class": "rate_limit",
            "reset": self.reset,
            "message": "You've hit your limit",
        }
        (self.recordings / "builder.json").write_text(json.dumps(rate_limited))
        self.append_events(RUNNING_S3)
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            "build-task",
            "--slot",
            "build",
            "--project",
            "shop",
            "--cwd",
            str(self.project.path),
            "--wave",
            "shop_w1",
            "--task",
            "S3",
            "task=@TASK.S3",
            environment=self.describe_environment(),
        )
        (self.recordings / "builder.json").write_text(json.dumps(RESUMED_RESULT))
        self.rate_limited_run = self.read_run_records()[0]["run"]

    def append_events(self, lines: str) -> None:
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(lines)

    def read_segment_result(self, number: int) -> dict:
        path = self.state / "runs" / self.rate_limited_run / "segments" / str(number) / "result.json"
        self.wait_for_file(path)
        return json.loads(path.read_text())


class BrigadeTickPausingOnARateLimitTest(RateLimitedRunTestCase):
    def test_should_pause_every_running_wave_on_the_quota_until_the_hour_of_the_reset(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("wave.paused"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "wave.paused",
                    "wave": "shop_w1",
                    "reason": "quota",
                    "resume_at": ANY,
                }
            ],
        )
        self.assertRegex(self.read_events("wave.paused")[0]["resume_at"], RESUME_AT_15)

    def test_should_move_the_rate_limited_task_to_paused_quota_and_launch_no_task_of_the_paused_wave(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.read_events("task.state")[-1]["state"], "paused:quota")
        self.assertEqual([record["run"] for record in self.read_run_records()], [self.rate_limited_run])


class BrigadeTickPausingOnARateLimitWithoutResetTest(RateLimitedRunTestCase):
    reset = NO_RESET

    def test_should_pause_the_wave_until_thirty_minutes_after_the_clock_of_the_tick(self):
        # Arrange
        before = datetime.now(UTC).replace(microsecond=0)

        # Act
        self.run_tick("--once")

        # Assert
        after = datetime.now(UTC)
        resume_at = datetime.fromisoformat(self.read_events("wave.paused")[0]["resume_at"])
        self.assertGreaterEqual(resume_at, before + timedelta(minutes=30))
        self.assertLessEqual(resume_at, after + timedelta(minutes=30))


class BrigadeTickResumingThroughResumeArgvTest(RateLimitedRunTestCase):
    client_operations = "resume"

    def setUp(self):
        super().setUp()
        self.append_events(PAUSED_ON_THE_QUOTA_UNTIL_THE_PAST)

    def test_should_resume_the_run_as_its_next_segment_in_the_session_of_its_last_one(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.read_segment_result(2)["session"], RATE_LIMITED_SESSION)

    def test_should_record_the_wave_resumed_and_move_the_task_back_to_running(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.read_events("wave.resumed"),
            [{"schema_version": 1, "ts": ANY, "event": "wave.resumed", "wave": "shop_w1", "reason": "quota"}],
        )
        self.assertEqual(self.read_events("task.state")[-1]["state"], "running")


class BrigadeTickResumingThroughAFreshLaunchTest(RateLimitedRunTestCase):
    def setUp(self):
        super().setUp()
        self.append_events(PAUSED_ON_THE_QUOTA_UNTIL_THE_PAST)

    def test_should_relaunch_the_run_as_its_next_segment_on_a_brief_opening_on_its_progress(self):
        # Act
        self.run_tick("--once")

        # Assert
        result = self.read_segment_result(2)
        brief = (self.state / "runs" / self.rate_limited_run / "segments" / "2" / "brief.md").read_text()
        self.assertNotEqual(result["session"], RATE_LIMITED_SESSION)
        self.assertTrue(brief.startswith("# Progress so far\n"), brief)


class BrigadeTickPausingOnAnUnavailableForgeAccountTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(FORGE_ACCOUNT_UNAVAILABLE)

    def test_should_pause_every_running_wave_on_the_forge_account_and_launch_none_of_its_tasks(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.read_events("wave.paused"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "wave.paused",
                    "wave": "shop_w1",
                    "reason": "forge_account",
                    "resume_at": None,
                }
            ],
        )
        self.assertEqual(self.read_run_records(), [])


class BrigadeWaveResumeTest(WaveTickTestCase):
    def setUp(self):
        super().setUp()
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(PAUSED_ON_THE_FORGE_ACCOUNT)

    def run_wave_resume(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "resume", *arguments, environment=self.describe_environment()
        )

    def read_events(self, name: str) -> list:
        lines = (self.state / "ledger" / "2026-10.jsonl").read_text().splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def test_should_resume_every_wave_paused_on_the_forge_account_without_a_request(self):
        # Act
        completed = self.run_wave_resume()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("wave.resumed"),
            [{"schema_version": 1, "ts": ANY, "event": "wave.resumed", "wave": "shop_w1", "reason": "forge_account"}],
        )

    def test_should_resume_the_wave_of_the_request_named(self):
        # Act
        completed = self.run_wave_resume("shop_1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "wave shop_w1 resumed\n")
        self.assertEqual([event["wave"] for event in self.read_events("wave.resumed")], ["shop_w1"])

    def test_should_exit_1_naming_the_state_of_a_wave_that_is_not_paused(self):
        # Arrange
        self.run_wave_resume("shop_1")

        # Act
        completed = self.run_wave_resume("shop_1")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertRegex(completed.stderr, re.escape("the wave shop_w1 of @REQUEST.shop_1 is running, not paused"))
