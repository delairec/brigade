import unittest
from pathlib import Path

from brigade.git.is_on_a_remote import is_on_a_remote
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

CONTAINING_REMOTE_REF = (
    "git",
    "for-each-ref",
    "--count=1",
    "--contains",
    "c0ffee1",
    "--format=%(refname)",
    "refs/remotes",
)


class IsOnARemoteTest(unittest.TestCase):
    def test_should_tell_whether_a_remote_tracking_ref_contains_the_commit(self):
        for listing, on_a_remote in [("refs/remotes/origin/main\n", True), ("", False)]:
            with self.subTest(listing=listing):
                # Arrange
                git = RecordingProcessRunner({CONTAINING_REMOTE_REF: ProcessAnswer(stdout=listing)})

                # Act
                answer = is_on_a_remote(git, Path("/srv/shop"), "c0ffee1")

                # Assert
                self.assertEqual(answer, on_a_remote)
