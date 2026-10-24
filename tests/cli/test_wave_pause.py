import json
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_tick import WaveTickTestCase

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

    def read_events(self, name: str) -> list:
        lines = (self.state / "ledger" / "2026-10.jsonl").read_text().splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

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
            self.read_events("wave.resumed"),
            [{"schema_version": 1, "ts": ANY, "event": "wave.resumed", "wave": "shop_w1", "reason": "forge_account"}],
        )
