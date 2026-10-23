import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_thread_reply import ThreadReply, ask_thread_reply
from tests.unit.forge_double import ForgeDouble, ForgeRequest

NO_RUNTIME_NEEDED = None
REPLY = ThreadReply(
    repository="/projects/shop", thread="PRRT_kwDOA1", body="fixed by 8885daa", environment={"GH_TOKEN": "t"}
)


class AskThreadReplyTest(unittest.TestCase):
    def test_should_refuse_an_answer_of_another_schema_version_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"reply_review_thread": lambda request: {"schema_version": 2}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_thread_reply(forge, "github", REPLY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertRegex(str(refusal.exception), "^forge plugin github answered reply_review_thread: ")

    def test_should_ask_the_forge_to_reply_on_the_thread_of_the_reply(self):
        # Arrange
        forge = ForgeDouble({"reply_review_thread": lambda request: {"schema_version": 1}})

        # Act
        ask_thread_reply(forge, "github", REPLY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                ForgeRequest(
                    "reply_review_thread",
                    {
                        "schema_version": 1,
                        "repository": "/projects/shop",
                        "thread": "PRRT_kwDOA1",
                        "body": "fixed by 8885daa",
                        "environment": {"GH_TOKEN": "t"},
                    },
                )
            ],
        )
