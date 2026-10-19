import unittest
from pathlib import Path

from brigade.git.resolve_commit import resolve_commit
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

VERIFY_COMMIT = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "v1.2^{commit}")


class ResolveCommitTest(unittest.TestCase):
    def test_should_answer_the_commit_the_ref_names(self):
        # Arrange
        git = RecordingProcessRunner({VERIFY_COMMIT: ProcessAnswer(stdout="4f2a9c1d\n")})

        # Act
        sha = resolve_commit(git, Path("/srv/shop"), "v1.2")

        # Assert
        self.assertEqual(sha, "4f2a9c1d")

    def test_should_answer_none_for_a_ref_naming_no_commit(self):
        # Arrange
        git = RecordingProcessRunner({VERIFY_COMMIT: ProcessAnswer(exit_code=1)})

        # Act
        sha = resolve_commit(git, Path("/srv/shop"), "v1.2")

        # Assert
        self.assertIsNone(sha)
