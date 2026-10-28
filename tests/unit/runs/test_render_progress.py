import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.render_progress import render_progress

NO_RUNTIME_NEEDED = None
PROGRESS_FILE = Path("/state/runs/20261007T090000Z-b70a01/progress.awawa")
STEP_ENTITY = {"type": "STEP", "name": "s1", "fields": [{"name": "DONE", "value": "read the task"}]}


class DocumentPluginDouble:
    def __init__(self, *, holds_entry: bool):
        self.holds_entry = holds_entry
        self.requests = []

    def detect_entry(self, request: dict, runtime) -> dict:
        self.requests.append(("detect_entry", request["document"], request["path"]))
        return {"schema_version": 1, "holds_entry": self.holds_entry}

    def render_document(self, request: dict, runtime) -> dict:
        self.requests.append(("render_document", request["document"], request["path"]))
        return {"schema_version": 1, "text": "STEP s1\n  DONE: read the task\n", "entities": [STEP_ENTITY]}


class RendererAnsweringNoTextDouble(DocumentPluginDouble):
    def render_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "entities": None}


class RenderProgressTest(unittest.TestCase):
    def test_should_render_the_progress_through_the_document_plugin(self):
        # Arrange
        document = DocumentPluginDouble(holds_entry=True)

        # Act
        progress = render_progress(PROGRESS_FILE, document, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(progress, {"text": "STEP s1\n  DONE: read the task\n", "entities": [STEP_ENTITY]})

    def test_should_ask_the_plugin_about_the_progress_file(self):
        # Arrange
        document = DocumentPluginDouble(holds_entry=True)

        # Act
        render_progress(PROGRESS_FILE, document, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            document.requests,
            [
                ("detect_entry", "progress", "/state/runs/20261007T090000Z-b70a01/progress.awawa"),
                ("render_document", "progress", "/state/runs/20261007T090000Z-b70a01/progress.awawa"),
            ],
        )

    def test_should_render_no_progress_from_a_file_holding_no_entry(self):
        # Arrange
        document = DocumentPluginDouble(holds_entry=False)

        # Act
        progress = render_progress(PROGRESS_FILE, document, NO_RUNTIME_NEEDED)

        # Assert
        self.assertIsNone(progress)

    def test_should_refuse_a_rendering_naming_the_plugin_of_the_file(self):
        # Arrange
        document = RendererAnsweringNoTextDouble(holds_entry=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            render_progress(PROGRESS_FILE, document, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "document plugin awawa answered render_document: lacks the key text")
