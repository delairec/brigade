import unittest

from brigade.system.transcripts_request import TranscriptsRequest

TRANSCRIPTS_DOCUMENT = {"schema_version": 1, "session_id": "session-b74", "worktree": "/home/user/tidepool"}


class TranscriptsRequestTest(unittest.TestCase):
    def test_should_write_back_the_document_it_read(self):
        # Act
        document = TranscriptsRequest.from_document(TRANSCRIPTS_DOCUMENT).to_document()

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "session_id": "session-b74", "worktree": "/home/user/tidepool"}
        )
