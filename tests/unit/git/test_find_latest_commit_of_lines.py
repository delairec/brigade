import unittest
from pathlib import Path

from brigade.git.find_latest_commit_of_lines import LinesOfFile, find_latest_commit_of_lines
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

BLAME = (
    "1111111111111111111111111111111111111111 46 46 1\n"
    "author Ada\n"
    "committer-time 1763000000\n"
    '\tSOURCE "the user\'s rulings"\n'
    "2222222222222222222222222222222222222222 47 47 2\n"
    "author Ada\n"
    "committer-time 1763200000\n"
    '\t\t+ "of 2026-11-13"\n'
    "2222222222222222222222222222222222222222 48 48\n"
    "\t\tREF @TASK.T1\n"
)


class FindLatestCommitOfLinesTest(unittest.TestCase):
    def test_should_answer_the_most_recent_commit_blamed_for_the_lines_at_head(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                ("git", "blame", "--porcelain", "-L", "46,48", "HEAD", "--", "corpus/tasks.awawa"): ProcessAnswer(
                    stdout=BLAME
                )
            }
        )
        source_lines = LinesOfFile(repository=Path("/srv/shop"), path="corpus/tasks.awawa", first=46, last=48)

        # Act
        commit = find_latest_commit_of_lines(git, source_lines)

        # Assert
        self.assertEqual(commit, "2222222222222222222222222222222222222222")
