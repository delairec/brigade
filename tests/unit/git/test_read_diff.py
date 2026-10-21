import unittest
from pathlib import Path

from brigade.git.read_diff import read_diff
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

DIFF = "--- a/cart.py\n+++ b/cart.py\n@@ -0,0 +1 @@\n+def empty_cart():\n"


class ReadDiffTest(unittest.TestCase):
    def test_should_answer_the_diff_between_two_commits(self):
        # Arrange
        git = RecordingProcessRunner({("git", "diff", "0000000", "2222222"): ProcessAnswer(stdout=DIFF)})

        # Act
        record = read_diff(git, Path("/srv/shop"), "0000000", "2222222")

        # Assert
        self.assertEqual(record.stdout, DIFF)
