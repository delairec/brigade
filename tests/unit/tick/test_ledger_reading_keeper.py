import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_started import WaveStarted
from brigade.tick.ledger_reading_keeper import LedgerReadingKeeper
from tests.unit.ledger_reader_double import LedgerReaderDouble

WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-10-18T09:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M4", "tasks": ["T7"]}\n'
)
WAVE_PAUSED = (
    '{"schema_version": 1, "ts": "2026-10-18T09:30:00Z", "event": "wave.paused", "wave": "tidepool_w16",'
    ' "reason": "quota", "resume_at": null}\n'
)


class LedgerReadingKeeperTest(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.ledger = self.state_root / "ledger" / "2026-10.jsonl"
        self.ledger.parent.mkdir()
        self.ledger.write_text(WAVE_STARTED, encoding="utf-8")
        self.counter = LedgerReaderDouble()

    def test_should_read_the_ledger_once_however_often_it_is_asked(self):
        # Arrange
        keeper = LedgerReadingKeeper(self.counter.read)
        keeper.read(self.state_root)

        # Act
        keeper.read(self.state_root)

        # Assert
        self.assertEqual(self.counter.state_roots, [self.state_root])

    def test_should_extend_its_reading_with_the_events_appended_since(self):
        # Arrange
        keeper = LedgerReadingKeeper(self.counter.read)
        keeper.read(self.state_root)
        with self.ledger.open("a", encoding="utf-8") as ledger:
            ledger.write(WAVE_PAUSED)

        # Act
        reading = keeper.read(self.state_root)

        # Assert
        self.assertEqual(
            reading.entries,
            (
                LedgerEntry(
                    instant=datetime(2026, 10, 18, 9, 0, tzinfo=UTC),
                    event=WaveStarted(wave="tidepool_w16", project="tidepool", branch="integration/M4", tasks=("T7",)),
                ),
                LedgerEntry(
                    instant=datetime(2026, 10, 18, 9, 30, tzinfo=UTC),
                    event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                ),
            ),
        )
