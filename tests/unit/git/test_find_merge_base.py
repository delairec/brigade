import unittest
from pathlib import Path

from brigade.git.find_merge_base import find_merge_base
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class FindMergeBaseTest(unittest.TestCase):
    def test_should_answer_the_commit_both_refs_descend_from(self):
        # Arrange
        git = RecordingProcessRunner(
            {("git", "merge-base", "--end-of-options", "origin/main", "HEAD"): ProcessAnswer(stdout="4f2a9c1\n")}
        )

        # Act
        merge_base = find_merge_base(git, Path("/srv/shop"), "origin/main", "HEAD")

        # Assert
        self.assertEqual(merge_base, "4f2a9c1")
