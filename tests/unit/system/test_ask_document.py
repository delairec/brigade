import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_document import DocumentQuestion, ask_document

NO_RUNTIME_NEEDED = None
PROGRESS_REQUEST = {"schema_version": 1, "document": "progress", "path": "/state/runs/r1/progress.md"}


class EntryDetectorAnsweringATextDouble:
    def detect_entry(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "holds_entry": "yes"}


class EntryDetectorDouble:
    def __init__(self):
        self.requests = []

    def detect_entry(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return {"schema_version": 1, "holds_entry": True}


class CreatorAnsweringNothingDouble:
    def create_document(self, request: dict, runtime) -> None:
        return None


class AskDocumentTest(unittest.TestCase):
    def test_should_hand_the_request_to_the_operation_and_return_its_answer(self):
        # Arrange
        document = EntryDetectorDouble()
        question = DocumentQuestion(document_name="markdown", operation="detect_entry", request=PROGRESS_REQUEST)

        # Act
        answer = ask_document(document, question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            document.requests, [{"schema_version": 1, "document": "progress", "path": "/state/runs/r1/progress.md"}]
        )
        self.assertEqual(answer, {"schema_version": 1, "holds_entry": True})

    def test_should_refuse_an_answer_breaking_its_shape_naming_the_plugin_and_the_operation(self):
        # Arrange
        question = DocumentQuestion(document_name="awawa", operation="detect_entry", request=PROGRESS_REQUEST)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_document(EntryDetectorAnsweringATextDouble(), question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "document plugin awawa answered detect_entry: holds_entry is a string, not a boolean",
        )

    def test_should_refuse_a_creation_answering_no_document(self):
        # Arrange
        question = DocumentQuestion(document_name="markdown", operation="create_document", request=PROGRESS_REQUEST)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_document(CreatorAnsweringNothingDouble(), question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "document plugin markdown answered create_document: the document is null, not an object",
        )
