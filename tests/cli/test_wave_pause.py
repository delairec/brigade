from unittest.mock import ANY

from tests.cli.read_ledger_events import read_ledger_events
from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.wave_tick_test_case import WaveTickTestCase

PAUSED_ON_THE_FORGE_ACCOUNT = (
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "wave.paused", "wave": "shop_w1",'
    ' "reason": "forge_account", "resume_at": null}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "wave.paused", "wave": "cafe_w1",'
    ' "reason": "quota", "resume_at": "2026-10-13T12:00:00Z"}\n'
)


class BrigadeWaveResumeTest(WaveTickTestCase):
    def setUp(self):
        super().setUp()
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(PAUSED_ON_THE_FORGE_ACCOUNT)

    def read_events(self) -> list:
        return read_ledger_events(self.state)

    def test_should_resume_the_wave_named(self):
        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "resume", "shop_w1", environment=self.describe_environment()
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "wave shop_w1 resumed\n")
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-13T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/M1-empty-cart",
                    "tasks": ["S3", "S4", "S5", "S6"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:30:00Z",
                    "event": "task.state",
                    "wave": "cafe_w1",
                    "task": "S6",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T11:00:00Z",
                    "event": "wave.paused",
                    "wave": "shop_w1",
                    "reason": "forge_account",
                    "resume_at": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T11:00:00Z",
                    "event": "wave.paused",
                    "wave": "cafe_w1",
                    "reason": "quota",
                    "resume_at": "2026-10-13T12:00:00Z",
                },
                {"schema_version": 1, "ts": ANY, "event": "wave.resumed", "wave": "shop_w1", "reason": "forge_account"},
            ],
        )
