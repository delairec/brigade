import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_document import DocumentQuestion, ask_document
from brigade.system.document_creation import DocumentCreation
from brigade.system.document_rendering import DocumentRendering
from brigade.system.document_request import DocumentRequest
from brigade.system.document_text import DocumentText
from brigade.system.entry_detection import EntryDetection

NO_RUNTIME_NEEDED = None
PROGRESS_REQUEST = DocumentRequest(
    document="progress",
    path="/state/runs/r1/progress.md",
    schema='SCHEMA STEP\n\tDESC "a step the run completed"\n',
    frame=("a fact is what the next segment needs and no command gives back",),
    role_has_shell=True,
)


class DocumentPluginDouble:
    def __init__(self):
        self.requests = []

    def create_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1}

    def describe_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "text": "The progress is the Markdown file /state/runs/r1/progress.md.\n"}

    def read_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "text": "step 1 done\n"}

    def detect_entry(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return {"schema_version": 1, "holds_entry": True}

    def render_document(self, request: dict, runtime) -> dict:
        return {
            "schema_version": 1,
            "text": "STEP s1\n  DONE: read the task\n",
            "entities": [{"type": "STEP", "name": "s1", "fields": [{"name": "DONE", "value": "read the task"}]}],
        }


class EntryDetectorAnsweringATextDouble:
    def detect_entry(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "holds_entry": "yes"}


class RendererAnsweringTextEntitiesDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "text": "STEP s1\n", "entities": "STEP s1"}


class CreatorAnsweringNothingDouble:
    def create_document(self, request: dict, runtime) -> None:
        return None


class AskDocumentTest(unittest.TestCase):
    def test_should_hand_the_request_to_the_operation_as_a_document(self):
        # Arrange
        document = DocumentPluginDouble()
        question = DocumentQuestion(document_name="markdown", operation="detect_entry", request=PROGRESS_REQUEST)

        # Act
        ask_document(document, question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            document.requests,
            [
                {
                    "schema_version": 1,
                    "document": "progress",
                    "path": "/state/runs/r1/progress.md",
                    "schema": 'SCHEMA STEP\n\tDESC "a step the run completed"\n',
                    "frame": ["a fact is what the next segment needs and no command gives back"],
                    "shell": True,
                }
            ],
        )

    def test_should_read_the_answer_of_each_operation_into_its_kind(self):
        # Arrange
        rows = [
            ("create_document", DocumentCreation()),
            (
                "describe_document",
                DocumentText(text="The progress is the Markdown file /state/runs/r1/progress.md.\n"),
            ),
            ("read_document", DocumentText(text="step 1 done\n")),
            ("detect_entry", EntryDetection(holds_entry=True)),
            (
                "render_document",
                DocumentRendering(
                    text="STEP s1\n  DONE: read the task\n",
                    entities=[{"type": "STEP", "name": "s1", "fields": [{"name": "DONE", "value": "read the task"}]}],
                ),
            ),
        ]
        for operation, expected_answer in rows:
            with self.subTest(operation=operation):
                # Arrange
                question = DocumentQuestion(document_name="markdown", operation=operation, request=PROGRESS_REQUEST)

                # Act
                answer = ask_document(DocumentPluginDouble(), question, NO_RUNTIME_NEEDED)

                # Assert
                self.assertEqual(answer, expected_answer)

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

    def test_should_refuse_a_rendering_whose_entities_are_no_list(self):
        # Arrange
        question = DocumentQuestion(document_name="awawa", operation="render_document", request=PROGRESS_REQUEST)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_document(RendererAnsweringTextEntitiesDouble(), question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "document plugin awawa answered render_document: entities is a string, not a list",
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
