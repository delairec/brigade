import unittest
from pathlib import Path

from brigade.git.read_file_diff import FileSince, read_file_diff
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

DIFF = "@@ -1,0 +2,2 @@\n+a\n+b\n"


class ReadFileDiffTest(unittest.TestCase):
    def test_should_answer_the_changes_of_a_file_since_a_commit_without_context(self):
        # Arrange
        git = RecordingProcessRunner(
            {("git", "diff", "-U0", "4f2a9c1", "HEAD", "--", "brigade/cart.py"): ProcessAnswer(stdout=DIFF)}
        )
        cart = FileSince(repository=Path("/srv/shop"), path="brigade/cart.py", since="4f2a9c1")

        # Act
        diff = read_file_diff(git, cart)

        # Assert
        self.assertEqual(diff, DIFF)
