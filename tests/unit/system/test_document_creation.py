import unittest

from brigade.system.document_creation import DocumentCreation


class DocumentCreationTest(unittest.TestCase):
    def test_should_read_a_creation_answering_its_schema_version_alone(self):
        # Act
        creation = DocumentCreation.from_document({"schema_version": 1})

        # Assert
        self.assertEqual(creation, DocumentCreation())
