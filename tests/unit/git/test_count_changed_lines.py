import unittest
from pathlib import Path

from brigade.git.count_changed_lines import ChangedFile, count_changed_lines
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class CountChangedLinesTest(unittest.TestCase):
    def test_should_count_the_insertions_and_deletions_of_each_file(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                ("git", "diff", "--numstat", "--text", "--end-of-options", "origin/main", "HEAD", "--"): ProcessAnswer(
                    stdout="3\t1\tbrigade/cli.py\n10\t0\tdocs/a\tb.md\n"
                )
            }
        )

        # Act
        changed = count_changed_lines(git, Path("/srv/shop"), "origin/main", "HEAD")

        # Assert
        self.assertEqual(
            changed,
            (
                ChangedFile(path="brigade/cli.py", insertions=3, deletions=1),
                ChangedFile(path="docs/a\tb.md", insertions=10, deletions=0),
            ),
        )
