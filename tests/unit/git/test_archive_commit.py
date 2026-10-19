import unittest
from pathlib import Path

from brigade.git.archive_commit import archive_commit
from tests.unit.recording_process_runner import RecordingProcessRunner


class ArchiveCommitTest(unittest.TestCase):
    def test_should_write_the_commit_as_a_tar_archive_at_the_destination(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        archive_commit(git, Path("/srv/shop"), "4f2a9c1", Path("/var/cache/commit.tar"))

        # Assert
        self.assertEqual(
            git.commands,
            [("/srv/shop", ("git", "archive", "--format=tar", "--output=/var/cache/commit.tar", "4f2a9c1"))],
        )
