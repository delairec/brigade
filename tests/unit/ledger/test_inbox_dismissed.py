import unittest

from brigade.ledger.inbox_dismissed import InboxDismissed


class InboxDismissedTest(unittest.TestCase):
    def test_should_read_the_signal_dismissed_from_the_inbox(self):
        # Act
        event = InboxDismissed.from_document(
            {"event": "inbox.dismissed", "fingerprint": "note:2c26b46b68ff", "kind": "note", "project": "oak"}
        )

        # Assert
        self.assertEqual(event, InboxDismissed(fingerprint="note:2c26b46b68ff", kind="note", project="oak"))

    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"fingerprint": "rt:PRRT_kwDO", "kind": "review_thread", "project": None}

        # Act
        written = InboxDismissed.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"fingerprint": "rt:PRRT_kwDO", "kind": "review_thread", "project": None})
