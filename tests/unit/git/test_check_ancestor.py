import unittest
from pathlib import Path

from brigade.git.check_ancestor import check_ancestor
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

IS_ANCESTOR = ("git", "merge-base", "--is-ancestor", "origin/main", "feat/b42")


class CheckAncestorTest(unittest.TestCase):
    def test_should_answer_the_verdict_of_git_whichever_it_is(self):
        for exit_code in [0, 1]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner({IS_ANCESTOR: ProcessAnswer(exit_code=exit_code)})

                # Act
                record = check_ancestor(git, Path("/srv/shop"), "origin/main", "feat/b42")

                # Assert
                self.assertEqual(record.exit_code, exit_code)
