import unittest
from pathlib import Path

from brigade.git.cut_branch import BranchCut, cut_branch
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

CUT_BRANCH = ("git", "branch", "--quiet", "integration/shop_w2", "main")


class CutBranchTest(unittest.TestCase):
    def test_should_create_the_branch_on_its_start_in_the_repository(self):
        # Arrange
        git = RecordingProcessRunner({CUT_BRANCH: ProcessAnswer()})

        # Act
        cut_branch(git, BranchCut(repository=Path("/srv/shop"), branch="integration/shop_w2", start="main"))

        # Assert
        self.assertEqual(git.requests, [ProcessRequest(argv=CUT_BRANCH, cwd="/srv/shop", timeout_s=10.0)])
