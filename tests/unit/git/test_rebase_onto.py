import unittest
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.git.rebase_onto import rebase_onto
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

REBASE = ("git", "rebase", "origin/integration/M4")
REBASE_IN_PROGRESS = ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD")
ABORT = ("git", "rebase", "--abort")
STOPPED = ProcessAnswer(exit_code=1, stderr="error: cannot rebase: You have unstaged changes.")
STOPPED_ON_A_CONFLICT = ProcessAnswer(exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py")
NO_REBASE_IN_PROGRESS = ProcessAnswer(exit_code=1)
REBASE_STOPPED_AT_A_COMMIT = ProcessAnswer(stdout="f02da32\n")


class RebaseOntoTest(unittest.TestCase):
    def test_should_tell_whether_the_rebase_applied_and_abort_one_that_conflicts(self):
        for case, answers, applied, argvs in [
            ("applied", {}, True, [REBASE]),
            (
                "in conflict",
                {REBASE: STOPPED_ON_A_CONFLICT, REBASE_IN_PROGRESS: REBASE_STOPPED_AT_A_COMMIT},
                False,
                [REBASE, REBASE_IN_PROGRESS, ABORT],
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                git = RecordingProcessRunner(answers)

                # Act
                rebased = rebase_onto(git, Path("/srv/shop"), "origin/integration/M4")

                # Assert
                self.assertEqual((rebased, [request.argv for request in git.requests]), (applied, argvs))

    def test_should_fail_with_the_refusal_of_git_when_the_rebase_stopped_on_no_conflict(self):
        # Arrange
        git = RecordingProcessRunner({REBASE: STOPPED, REBASE_IN_PROGRESS: NO_REBASE_IN_PROGRESS})

        # Act
        with self.assertRaises(CommandFailed) as refusal:
            rebase_onto(git, Path("/srv/shop"), "origin/integration/M4")

        # Assert
        self.assertEqual(
            (str(refusal.exception), [request.argv for request in git.requests]),
            (
                "git rebase origin/integration/M4 exited 1: error: cannot rebase: You have unstaged changes.",
                [REBASE, REBASE_IN_PROGRESS],
            ),
        )
