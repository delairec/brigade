import unittest

from brigade.system.transcripts_answer import TranscriptsAnswer

TRANSCRIPTS_DOCUMENT = {
    "schema_version": 1,
    "messages": [
        {"role": "user", "timestamp": "2026-10-08T09:00:00Z", "content": "Deliver the task."},
        {"role": "assistant", "timestamp": None, "content": [{"type": "text", "text": "Done."}]},
    ],
}


class TranscriptsAnswerTest(unittest.TestCase):
    def test_should_write_back_the_messages_it_read(self):
        # Act
        document = TranscriptsAnswer.from_document(TRANSCRIPTS_DOCUMENT).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "messages": [
                    {"role": "user", "timestamp": "2026-10-08T09:00:00Z", "content": "Deliver the task."},
                    {"role": "assistant", "timestamp": None, "content": [{"type": "text", "text": "Done."}]},
                ],
            },
        )
