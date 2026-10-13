import tempfile
import unittest
from pathlib import Path

from brigade.adapters.documents.markdown import (
    create_document,
    describe_document,
    detect_entry,
    read_document,
    render_document,
)

NO_SCHEMA = None
NO_RUNTIME_NEEDED = None
FRAME = ["one entry per major step", "never command output"]


class MarkdownDocumentTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.md"

    def describe_request(self, role_has_shell: bool = True) -> dict:
        return {
            "document": "progress",
            "path": str(self.path),
            "schema": NO_SCHEMA,
            "frame": FRAME,
            "shell": role_has_shell,
        }


class MarkdownDocumentCreationTest(MarkdownDocumentTestCase):
    def test_should_create_an_empty_file(self):
        # Act
        create_document(self.describe_request())

        # Assert
        self.assertEqual(self.path.read_text(), "")


class MarkdownDocumentDescriptionTest(MarkdownDocumentTestCase):
    def test_should_name_the_file_its_form_and_the_frame_of_its_content(self):
        # Act
        description = describe_document(self.describe_request())

        # Assert
        self.assertEqual(
            description,
            {
                "text": f"The progress is the Markdown file {self.path}.\n\n"
                "- one entry per major step\n"
                "- never command output\n"
            },
        )


class MarkdownDocumentEntryTest(MarkdownDocumentTestCase):
    def test_should_answer_whether_the_file_holds_an_entry(self):
        for content, holds_entry in [("", False), ("\n  \n", False), ("step 1 done\n", True)]:
            with self.subTest(content=content):
                # Arrange
                self.path.write_text(content)

                # Act
                answer = detect_entry(self.describe_request())

                # Assert
                self.assertEqual(answer, {"holds_entry": holds_entry})


class MarkdownDocumentReadingTest(MarkdownDocumentTestCase):
    def test_should_give_a_resuming_run_the_file_as_it_is(self):
        # Arrange
        self.path.write_text("## step 1\n- branch feat/x\n")

        # Act
        reading = read_document(self.describe_request(), NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(reading, {"text": "## step 1\n- branch feat/x\n"})

    def test_should_render_the_file_as_it_is_for_a_person(self):
        # Arrange
        self.path.write_text("## step 1\n- branch feat/x\n")

        # Act
        rendering = render_document(self.describe_request(), NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(rendering, {"text": "## step 1\n- branch feat/x\n", "entities": None})
