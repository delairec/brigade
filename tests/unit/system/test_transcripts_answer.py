import unittest

from brigade.system.transcripts_answer import TranscriptsAnswer

TRANSCRIPTS_DOCUMENT = {
    "schema_version": 1,
    "messages": [
        {
            "role": "user",
            "timestamp": "2026-10-08T09:00:00Z",
            "content": "Deliver the task.",
            "tool_calls": 0,
            "id": None,
            "usage": None,
        },
        {
            "role": "assistant",
            "timestamp": None,
            "content": [{"type": "tool_use", "name": "Read"}],
            "tool_calls": 1,
            "id": "msg_01",
            "usage": {
                "input_tokens": 3,
                "output_tokens": 412,
                "cache_creation_input_tokens": 2048,
                "cache_read_input_tokens": 16384,
            },
        },
    ],
    "subagents": [
        {
            "messages": [
                {
                    "role": "user",
                    "timestamp": None,
                    "content": "Make it pass.",
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                }
            ]
        },
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
                    {
                        "role": "user",
                        "timestamp": "2026-10-08T09:00:00Z",
                        "content": "Deliver the task.",
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    },
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": [{"type": "tool_use", "name": "Read"}],
                        "tool_calls": 1,
                        "id": "msg_01",
                        "usage": {
                            "input_tokens": 3,
                            "output_tokens": 412,
                            "cache_creation_input_tokens": 2048,
                            "cache_read_input_tokens": 16384,
                        },
                    },
                ],
                "subagents": [
                    {
                        "messages": [
                            {
                                "role": "user",
                                "timestamp": None,
                                "content": "Make it pass.",
                                "tool_calls": 0,
                                "id": None,
                                "usage": None,
                            }
                        ]
                    },
                ],
            },
        )
