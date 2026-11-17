import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.resolve_output import resolve_output

NO_SEARCH_PATH = ""


class ResolveOutputTest(unittest.TestCase):
    def test_should_accept_the_outputs_brigade_publishes_itself(self):
        for output in (
            "inbox",
            "issue",
            "file:docs/report-{run}.md",
            "entity:REPORT",
            "pr-file:{pr}:docs/reports/{pr}.md",
        ):
            with self.subTest(output):
                # Act
                resolved = resolve_output(output, NO_SEARCH_PATH)

                # Assert
                self.assertIsNone(resolved)

    def test_should_accept_an_output_executable_on_path(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        executable = Path(directory.name) / "brigade-output-slack"
        executable.write_text("#!/bin/sh\n")
        executable.chmod(0o755)

        # Act
        resolved = resolve_output("slack", directory.name)

        # Assert
        self.assertIsNone(resolved)

    def test_should_refuse_an_output_brigade_does_not_publish_and_no_executable_answers(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_output("slack", NO_SEARCH_PATH)

        # Assert
        self.assertEqual(str(raised.exception), "no output slack: no brigade-output-slack on PATH")
