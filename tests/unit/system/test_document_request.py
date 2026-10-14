import unittest

from brigade.system.document_request import DocumentRequest


class DocumentRequestTest(unittest.TestCase):
    def test_should_write_the_request_of_a_document_operation_with_its_schema_version(self):
        # Arrange
        request = DocumentRequest(
            document="progress",
            path="/state/brigade/runs/r1/progress.awawa",
            schema='SCHEMA STEP\n\tDESC "a step the run completed"\n',
            frame=("a fact is what the next segment needs and no command gives back",),
            role_has_shell=True,
        )

        # Act
        document = request.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "document": "progress",
                "path": "/state/brigade/runs/r1/progress.awawa",
                "schema": 'SCHEMA STEP\n\tDESC "a step the run completed"\n',
                "frame": ["a fact is what the next segment needs and no command gives back"],
                "shell": True,
            },
        )
