import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_thread_reply import ThreadReply, ask_thread_reply

NO_RUNTIME_NEEDED = None
REPLY = ThreadReply(
    repository="/projects/shop", thread="PRRT_kwDOA1", body="fixed by 8885daa", environment={"GH_TOKEN": "t"}
)


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def reply_review_thread(self, request, runtime):
        self.requests.append(request)
        return self.answer


class AskThreadReplyTest(unittest.TestCase):
    def test_should_refuse_an_answer_of_another_schema_version_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 2})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_thread_reply(forge, "github", REPLY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertRegex(str(refusal.exception), "^forge plugin github answered reply_review_thread: ")

    def test_should_ask_the_forge_to_reply_on_the_thread_of_the_reply(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        ask_thread_reply(forge, "github", REPLY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                {
                    "schema_version": 1,
                    "repository": "/projects/shop",
                    "thread": "PRRT_kwDOA1",
                    "body": "fixed by 8885daa",
                    "environment": {"GH_TOKEN": "t"},
                }
            ],
        )
