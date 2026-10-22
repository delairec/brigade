import unittest
from pathlib import Path

from brigade.git.list_conflicting_files import list_conflicting_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

MERGE_TREE = ("git", "merge-tree", "--write-tree", "--name-only", "--no-messages", "HEAD", "origin/integration/M1")


class ListConflictingFilesTest(unittest.TestCase):
    def test_should_give_the_files_git_reports_in_conflict_after_the_tree_it_writes(self):
        for case, merge, conflicts in [
            ("two files in conflict", ProcessAnswer(stdout="4b825dc\nsrc/tides.py\nREADME.md\n", exit_code=1), ["src/tides.py", "README.md"]),
            ("no file in conflict", ProcessAnswer(stdout="4b825dc\n"), []),
        ]:
            with self.subTest(case=case):
                # Arrange
                git = RecordingProcessRunner({MERGE_TREE: merge})

                # Act
                files = list_conflicting_files(git, Path("/srv/shop"), "origin/integration/M1")

                # Assert
                self.assertEqual(files, conflicts)
