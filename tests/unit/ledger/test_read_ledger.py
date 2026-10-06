import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from brigade.ledger.read_ledger import LedgerEntry, LedgerReading, SkippedLine, read_ledger

WAVE_STARTED = (
    '{"schema_version": 1, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tp/16",'
    ' "project": "tidepool"}\n'
)
WAVE_PAUSED = '{"schema_version": 1, "ts": "2026-10-01T00:15:00Z", "event": "wave.paused", "wave": "tp/16"}\n'
UNDECLARED_EVENT = '{"schema_version": 1, "ts": "2026-10-01T00:20:00Z", "event": "study.done", "study": "health"}\n'


class ReadLedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        self.ledger = self.state_root / "ledger"

    def tearDown(self):
        self.root.cleanup()

    def write_ledger(self, file_name: str, content: bytes) -> Path:
        ledger_file = self.ledger / file_name
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger_file.write_bytes(content)
        return ledger_file


class ReadLedgerWhenNoLedgerWasWritten(ReadLedgerTestCase):
    def test_should_read_nothing(self):
        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(reading, LedgerReading(entries=(), files=(), skipped=()))


class ReadLedgerWhenEveryLineIsWhole(ReadLedgerTestCase):
    def test_should_read_the_monthly_files_in_order_and_ignore_the_other_files(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", (WAVE_PAUSED + UNDECLARED_EVENT).encode())
        september = self.write_ledger("2026-09.jsonl", WAVE_STARTED.encode())
        self.write_ledger("notes.txt", b"not a ledger file\n")

        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=timezone.utc),
                        record={
                            "schema_version": 1,
                            "ts": "2026-09-30T22:00:00Z",
                            "event": "wave.started",
                            "wave": "tp/16",
                            "project": "tidepool",
                        },
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=timezone.utc),
                        record={
                            "schema_version": 1,
                            "ts": "2026-10-01T00:15:00Z",
                            "event": "wave.paused",
                            "wave": "tp/16",
                        },
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 20, tzinfo=timezone.utc),
                        record={
                            "schema_version": 1,
                            "ts": "2026-10-01T00:20:00Z",
                            "event": "study.done",
                            "study": "health",
                        },
                    ),
                ),
                files=(str(september), str(october)),
                skipped=(),
            ),
        )


class ReadLedgerWhenALineFailsItsEnvelope(ReadLedgerTestCase):
    def test_should_skip_the_line_naming_its_file_its_number_and_the_reason(self):
        rows = [
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41\n', "not JSON"),
            (b"\xff\xfe\n", "not JSON"),
            (b"\n", "not JSON"),
            (b"[1, 2]\n", "the document is a list, not an object"),
            (
                b'{"ts": "2026-10-01T00:41:00Z", "event": "wave.paused", "wave": "tp/16"}\n',
                "lacks the key schema_version",
            ),
            (b'{"schema_version": 1, "event": "wave.paused", "wave": "tp/16"}\n', "lacks the key ts"),
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "wave": "tp/16"}\n', "lacks the key event"),
            (
                b'{"schema_version": 2, "ts": "2026-10-01T00:41:00Z", "event": "wave.paused", "wave": "tp/16"}\n',
                "schema_version is 2, not one of 1",
            ),
            (
                b'{"schema_version": 1, "ts": "yesterday", "event": "wave.paused", "wave": "tp/16"}\n',
                "ts 'yesterday' is not an ISO 8601 UTC instant",
            ),
            (
                b'{"schema_version": 1, "ts": "2026-10-01T02:41:00+02:00", "event": "wave.paused", "wave": "tp/16"}\n',
                "ts '2026-10-01T02:41:00+02:00' is not an ISO 8601 UTC instant",
            ),
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "event": "wave.paused"}\n', "lacks the key wave"),
        ]
        for content, expected_reason in rows:
            with self.subTest(content=content):
                # Arrange
                october = self.write_ledger("2026-10.jsonl", WAVE_PAUSED.encode() + content)

                # Act
                reading = read_ledger(self.state_root)

                # Assert
                self.assertEqual(
                    (len(reading.entries), reading.skipped),
                    (1, (SkippedLine(file=str(october), line=2, reason=expected_reason),)),
                )
