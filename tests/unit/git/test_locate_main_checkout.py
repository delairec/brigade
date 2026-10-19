import unittest
from pathlib import Path

from brigade.git.locate_main_checkout import locate_main_checkout
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class LocateMainCheckoutTest(unittest.TestCase):
    def test_should_answer_the_directory_holding_the_common_git_directory(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                    stdout="/srv/shop/.git\n"
                )
            }
        )

        # Act
        main_checkout = locate_main_checkout(git, Path("/srv/worktrees/b42"))

        # Assert
        self.assertEqual(main_checkout, Path("/srv/shop"))
