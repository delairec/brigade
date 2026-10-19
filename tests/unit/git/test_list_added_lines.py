import unittest
from pathlib import Path

from brigade.git.list_added_lines import AddedLine, list_added_lines
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

DIFF = (
    "git",
    "diff",
    "--unified=0",
    "--no-color",
    "--no-ext-diff",
    "--text",
    "--end-of-options",
    "origin/main",
    "HEAD",
    "--",
)
TWO_HUNKS = (
    "diff --git a/brigade/cli.py b/brigade/cli.py\n"
    "--- a/brigade/cli.py\n"
    "+++ b/brigade/cli.py\n"
    "@@ -10,0 +11,2 @@ def main():\n"
    "+first\n"
    "+second\n"
    "@@ -20 +22 @@\n"
    "-old\n"
    "+new\n"
)


class ListAddedLinesTest(unittest.TestCase):
    def test_should_number_each_added_line_in_the_file_it_lands_in(self):
        # Arrange
        git = RecordingProcessRunner({DIFF: ProcessAnswer(stdout=TWO_HUNKS)})

        # Act
        added = list_added_lines(git, Path("/srv/shop"), "origin/main", "HEAD")

        # Assert
        self.assertEqual(
            added,
            (
                AddedLine(path="brigade/cli.py", line=11, text="first"),
                AddedLine(path="brigade/cli.py", line=12, text="second"),
                AddedLine(path="brigade/cli.py", line=22, text="new"),
            ),
        )
