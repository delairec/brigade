import unittest

from brigade.system.ask_configured_client import ConfiguredClientAnswer
from brigade.system.describe_configured_client_answer import describe_configured_client_answer


class DescribeConfiguredClientAnswerTest(unittest.TestCase):
    def test_should_name_the_client_answering_then_each_slot_bound_elsewhere(self):
        # Arrange
        answer = ConfiguredClientAnswer(client="fake", slot_clients={"review": "codex"}, document={})

        # Act
        lines = describe_configured_client_answer(answer)

        # Assert
        self.assertEqual(lines, ["answers for fake", "slot review runs on codex"])
