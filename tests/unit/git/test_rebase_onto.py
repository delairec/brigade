import unittest
from pathlib import Path

from brigade.git.rebase_onto import rebase_onto
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

REBASE = ("git", "rebase", "origin/integration/M1")
ABORT = ("git", "rebase", "--abort")


class RebaseOntoTest(unittest.TestCase):
    def test_should_tell_whether_the_rebase_applied_and_abort_one_that_conflicts(self):
        for case, rebase_exit_code, applied, argvs in [
            ("applied", 0, True, [REBASE]),
            ("in conflict", 1, False, [REBASE, ABORT]),
        ]:
            with self.subTest(case=case):
                # Arrange
                git = RecordingProcessRunner({REBASE: ProcessAnswer(exit_code=rebase_exit_code)})

                # Act
                rebased = rebase_onto(git, Path("/srv/shop"), "origin/integration/M1")

                # Assert
                self.assertEqual((rebased, [request.argv for request in git.requests]), (applied, argvs))
