import unittest
from pathlib import Path

from brigade.git.commit_files import CommitRequest, commit_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

STAGED_DIFF = ("git", "diff", "--cached", "--quiet", "--", "projects.awawa")
REQUEST = CommitRequest(
    repository=Path("/srv/config"), files=("projects.awawa",), message="brigade project pause: shop"
)


class CommitFilesWithChangesTest(unittest.TestCase):
    def test_should_stage_the_files_and_commit_them(self):
        # Arrange
        git = RecordingProcessRunner({STAGED_DIFF: ProcessAnswer(exit_code=1)})

        # Act
        commit_files(git, REQUEST)

        # Assert
        self.assertEqual(
            git.commands,
            [
                ("/srv/config", ("git", "add", "--", "projects.awawa")),
                ("/srv/config", STAGED_DIFF),
                ("/srv/config", ("git", "commit", "--quiet", "-m", "brigade project pause: shop")),
            ],
        )


class CommitFilesWithoutChangesTest(unittest.TestCase):
    def test_should_stage_the_files_and_commit_nothing(self):
        # Arrange
        git = RecordingProcessRunner({STAGED_DIFF: ProcessAnswer(exit_code=0)})

        # Act
        commit_files(git, REQUEST)

        # Assert
        self.assertEqual(
            git.commands,
            [("/srv/config", ("git", "add", "--", "projects.awawa")), ("/srv/config", STAGED_DIFF)],
        )
