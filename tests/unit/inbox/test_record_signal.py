import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.ledger.inbox_recorded import InboxRecorded
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from tests.unit.create_test_paths import create_test_paths

RECORDED_AT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
NOTE_ON_OAK = NewSignal(
    kind="note", project="oak", fingerprint="note:474fa40ae4db", evidence={"text": "fix the flaky test"}
)


class RecordSignalTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.paths = create_test_paths(self.root)
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"


class RecordSignalInANewInboxTest(RecordSignalTestCase):
    def test_should_create_the_inbox_and_append_the_line_of_the_signal(self):
        # Act
        record_signal(self.paths, RECORDED_AT, NOTE_ON_OAK)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"),
            '{"schema_version": 1, "ts": "2026-10-24T09:00:00Z", "event": "recorded", "kind": "note",'
            ' "project": "oak", "fingerprint": "note:474fa40ae4db", "evidence": {"text": "fix the flaky test"}}\n',
        )

    def test_should_record_the_signal_in_the_ledger(self):
        # Act
        record_signal(self.paths, RECORDED_AT, NOTE_ON_OAK)

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries,
            (
                LedgerEntry(
                    instant=RECORDED_AT,
                    event=InboxRecorded(fingerprint="note:474fa40ae4db", kind="note", project="oak"),
                ),
            ),
        )


class RecordSignalInAnInboxAlreadyWrittenTest(RecordSignalTestCase):
    def test_should_append_after_the_lines_already_written(self):
        # Arrange
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text('{"earlier": "line"}\n', encoding="utf-8")

        # Act
        record_signal(self.paths, RECORDED_AT, NOTE_ON_OAK)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"),
            '{"earlier": "line"}\n'
            '{"schema_version": 1, "ts": "2026-10-24T09:00:00Z", "event": "recorded", "kind": "note",'
            ' "project": "oak", "fingerprint": "note:474fa40ae4db", "evidence": {"text": "fix the flaky test"}}\n',
        )
