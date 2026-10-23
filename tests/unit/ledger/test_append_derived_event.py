import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.wave_started import WaveStarted
from brigade.system.paths import Paths
from tests.unit.create_test_paths import PACKAGE_FILE

FIRST_WAVE_LINE = (
    '{"schema_version": 2, "ts": "2026-10-16T08:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/M1-empty-cart", "tasks": ["S3"]}\n'
)
SECOND_WAVE = WaveStarted(wave="shop_w2", project="shop", branch="integration/M2-undo", tasks=("S5", "S6"))


class AppendDerivedEventTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        self.ledger = root / "state" / "brigade" / "ledger"
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(FIRST_WAVE_LINE)
        self.paths = Paths(
            config_root=root / "config" / "brigade",
            state_root=root / "state" / "brigade",
            cache_root=root / "cache" / "brigade",
            home=root,
            executable_search_path="",
            package_file=PACKAGE_FILE,
        )
        self.readings = []

    def tearDown(self):
        self.root.cleanup()

    def derive_second_wave(self, reading: LedgerReading) -> WaveStarted:
        self.readings.append(reading)
        return SECOND_WAVE

    def test_should_derive_the_event_from_the_ledger_as_it_stands(self):
        # Act
        append_derived_event(self.paths, datetime(2026, 10, 17, 9, 0, tzinfo=UTC), self.derive_second_wave)

        # Assert
        [reading] = self.readings
        self.assertEqual(
            reading.entries,
            (
                LedgerEntry(
                    instant=datetime(2026, 10, 16, 8, 0, tzinfo=UTC),
                    event=WaveStarted(
                        wave="shop_w1", project="shop", branch="integration/M1-empty-cart", tasks=("S3",)
                    ),
                ),
            ),
        )

    def test_should_append_the_derived_event_to_the_ledger(self):
        # Act
        line = append_derived_event(self.paths, datetime(2026, 10, 17, 9, 0, tzinfo=UTC), self.derive_second_wave)

        # Assert
        self.assertEqual(
            line,
            {
                "schema_version": 2,
                "ts": "2026-10-17T09:00:00Z",
                "event": "wave.started",
                "wave": "shop_w2",
                "project": "shop",
                "branch": "integration/M2-undo",
                "tasks": ["S5", "S6"],
            },
        )
        self.assertEqual(
            json.loads((self.ledger / "2026-10.jsonl").read_text().splitlines()[1]),
            {
                "schema_version": 2,
                "ts": "2026-10-17T09:00:00Z",
                "event": "wave.started",
                "wave": "shop_w2",
                "project": "shop",
                "branch": "integration/M2-undo",
                "tasks": ["S5", "S6"],
            },
        )
