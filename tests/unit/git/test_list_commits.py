import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from brigade.git.list_commits import Commit, list_commits
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LOG = (
    "git",
    "log",
    "--since=2025-10-01 00:00:00 +0000",
    "--format=%x1e%H%x1f%an%x1f%at%x1f%s",
    "--name-only",
    "HEAD",
    "--",
)


class ListCommitsTest(unittest.TestCase):
    def test_should_list_the_commits_since_the_day_with_the_files_they_touch(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                LOG: ProcessAnswer(
                    stdout="\x1eabc\x1fAda\x1f1760000000\x1ffeat: add\n\nbrigade/cli.py\nREADME.md\n"
                    "\x1edef\x1fBob\x1f1760003600\x1fchore: empty\n"
                )
            }
        )

        # Act
        commits = list_commits(git, Path("/srv/shop"), date(2025, 10, 1))

        # Assert
        self.assertEqual(
            commits,
            (
                Commit(
                    sha="abc",
                    author="Ada",
                    date=datetime(2025, 10, 9, 8, 53, 20, tzinfo=UTC),
                    subject="feat: add",
                    files=("brigade/cli.py", "README.md"),
                ),
                Commit(
                    sha="def",
                    author="Bob",
                    date=datetime(2025, 10, 9, 9, 53, 20, tzinfo=UTC),
                    subject="chore: empty",
                    files=(),
                ),
            ),
        )
