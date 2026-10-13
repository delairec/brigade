import unittest

from brigade.system.document_text import DocumentText


class DocumentTextTest(unittest.TestCase):
    def test_should_read_the_text_a_document_plugin_answers(self):
        # Act
        text = DocumentText.from_document({"schema_version": 1, "text": "step 1 done\n"})

        # Assert
        self.assertEqual(text, DocumentText(text="step 1 done\n"))
