import unittest

from brigade.system.render_json import render_json


class RenderJsonTest(unittest.TestCase):
    def test_should_render_the_document_as_json_indented_by_two_spaces(self):
        # Arrange
        document = {"client": "fake", "argv": ["fake", "--resume"]}

        # Act
        text = render_json(document)

        # Assert
        self.assertEqual(text, '{\n  "client": "fake",\n  "argv": [\n    "fake",\n    "--resume"\n  ]\n}')
