import unittest
from pathlib import Path

from brigade.git.read_main_branch import read_main_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

ORIGIN_HEAD = ("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
CURRENT_BRANCH = ("git", "branch", "--show-current")
NO_ORIGIN_HEAD = ProcessAnswer(exit_code=1)


class ReadMainBranchTest(unittest.TestCase):
    def test_should_answer_the_branch_origin_head_points_at(self):
        # Arrange
        git = RecordingProcessRunner({ORIGIN_HEAD: ProcessAnswer(stdout="origin/trunk\n")})

        # Act
        main = read_main_branch(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(main, "trunk")

    def test_should_fall_back_on_the_branch_checked_out_without_origin_head(self):
        # Arrange
        git = RecordingProcessRunner({ORIGIN_HEAD: NO_ORIGIN_HEAD, CURRENT_BRANCH: ProcessAnswer(stdout="main\n")})

        # Act
        main = read_main_branch(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(main, "main")

    def test_should_answer_none_without_origin_head_nor_branch_checked_out(self):
        # Arrange
        git = RecordingProcessRunner({ORIGIN_HEAD: NO_ORIGIN_HEAD, CURRENT_BRANCH: ProcessAnswer(stdout="\n")})

        # Act
        main = read_main_branch(git, Path("/srv/shop"))

        # Assert
        self.assertIsNone(main)
