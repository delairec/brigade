import unittest
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.git.require_ancestor import require_ancestor
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

IS_ANCESTOR_OF_HEAD = ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD")


class RequireAncestorTest(unittest.TestCase):
    def test_should_pass_when_the_ref_is_an_ancestor_of_head(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        require_ancestor(git, Path("/srv/worktrees/b42"), "origin/main")

        # Assert
        self.assertEqual(git.commands, [("/srv/worktrees/b42", IS_ANCESTOR_OF_HEAD)])

    def test_should_fail_when_the_ref_is_not_an_ancestor_of_head(self):
        # Arrange
        git = RecordingProcessRunner({IS_ANCESTOR_OF_HEAD: ProcessAnswer(exit_code=1)})

        # Act / Assert
        with self.assertRaises(CommandFailed):
            require_ancestor(git, Path("/srv/worktrees/b42"), "origin/main")
