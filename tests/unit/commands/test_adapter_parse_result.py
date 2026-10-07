import unittest

from brigade.commands.adapter_parse_result import COMMAND


class AdapterParseResultTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "client": "fake"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "client": "fake"\n}')
