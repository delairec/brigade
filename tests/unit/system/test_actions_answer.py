import unittest

from brigade.system.actions_answer import ActionsAnswer


class ActionsAnswerTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"schema_version": 1, "actions": [{"kind": "text", "summary": "Reading the task"}]}

        # Act
        written = ActionsAnswer.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"schema_version": 1, "actions": [{"kind": "text", "summary": "Reading the task"}]})
