import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.inbox.dismiss_signal import dismiss_signal
from brigade.inbox.read_inbox import Signal
from brigade.ledger.inbox_dismissed import InboxDismissed
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from tests.unit.create_test_paths import create_test_paths

DISMISSED_AT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
NOTE_ON_OAK = Signal(
    id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
    fingerprint="note:474fa40ae4db",
    kind="note",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"text": "fix the flaky test"},
)


class DismissSignalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.paths = create_test_paths(self.root)
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"

    def test_should_append_the_line_naming_the_fingerprint_dismissed(self):
        # Act
        dismiss_signal(self.paths, DISMISSED_AT, NOTE_ON_OAK)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"),
            '{"schema_version": 1, "ts": "2026-10-24T09:00:00Z", "event": "dismissed",'
            ' "fingerprint": "note:474fa40ae4db"}\n',
        )

    def test_should_record_the_dismissal_in_the_ledger(self):
        # Act
        dismiss_signal(self.paths, DISMISSED_AT, NOTE_ON_OAK)

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries,
            (
                LedgerEntry(
                    instant=DISMISSED_AT,
                    event=InboxDismissed(fingerprint="note:474fa40ae4db", kind="note", project="oak"),
                ),
            ),
        )
