import unittest

from brigade.ledger.inbox_recorded import InboxRecorded


class InboxRecordedTest(unittest.TestCase):
    def test_should_read_the_signal_recorded_in_the_inbox(self):
        # Act
        event = InboxRecorded.from_document(
            {"event": "inbox.recorded", "fingerprint": "note:2c26b46b68ff", "kind": "note", "project": "oak"}
        )

        # Assert
        self.assertEqual(event, InboxRecorded(fingerprint="note:2c26b46b68ff", kind="note", project="oak"))

    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"fingerprint": "rt:PRRT_kwDO", "kind": "review_thread", "project": None}

        # Act
        written = InboxRecorded.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"fingerprint": "rt:PRRT_kwDO", "kind": "review_thread", "project": None})
