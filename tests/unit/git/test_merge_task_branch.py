import unittest
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.git.merge_task_branch import TaskBranchMerge, merge_task_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

MERGE = TaskBranchMerge(
    repository=Path("/srv/shop"),
    worktree=Path("/srv/shop/.brigade/worktrees/integration-cart"),
    branch="integration/cart",
    head="d3l1v3r",
    method="merge",
    message="merge @TASK.S1 into integration/cart",
)
LIST_WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
ADD_THE_WORKTREE = ("git", "worktree", "add", "--quiet", str(MERGE.worktree), "integration/cart")
RESET_THE_WORKTREE = ("git", "reset", "--quiet", "--hard", "integration/cart")
MERGE_WITH_A_COMMIT = ("git", "merge", "--quiet", "--no-ff", "-m", MERGE.message, "d3l1v3r")
MERGE_FAST_FORWARDING = ("git", "merge", "--quiet", "-m", MERGE.message, "d3l1v3r")
SQUASH = ("git", "merge", "--quiet", "--squash", "d3l1v3r")
COMMIT_THE_SQUASH = ("git", "commit", "--quiet", "-m", MERGE.message)
ABORT_THE_MERGE = ("git", "reset", "--quiet", "--merge")


def _merge_by(method: str, message: str = MERGE.message) -> TaskBranchMerge:
    return TaskBranchMerge(
        repository=MERGE.repository,
        worktree=MERGE.worktree,
        branch=MERGE.branch,
        head=MERGE.head,
        method=method,
        message=message,
    )


class MergeTaskBranchTest(unittest.TestCase):
    def test_should_merge_the_head_in_a_worktree_of_the_milestone_branch_by_the_method_of_the_project(self):
        for method, expected_merges in [
            ("merge", [MERGE_WITH_A_COMMIT]),
            ("rebase", [MERGE_FAST_FORWARDING]),
            ("squash", [SQUASH, COMMIT_THE_SQUASH]),
        ]:
            with self.subTest(method=method):
                # Arrange
                runner = RecordingProcessRunner({LIST_WORKTREES: ProcessAnswer(stdout="")})

                # Act
                merged = merge_task_branch(runner, _merge_by(method))

                # Assert
                self.assertTrue(merged)
                self.assertEqual(
                    runner.list_argvs(), [LIST_WORKTREES, ADD_THE_WORKTREE, RESET_THE_WORKTREE, *expected_merges]
                )

    def test_should_run_the_merge_in_the_worktree_of_the_milestone_branch(self):
        # Arrange
        runner = RecordingProcessRunner()

        # Act
        merge_task_branch(runner, _merge_by("merge"))

        # Assert
        self.assertEqual(runner.requests[-1].cwd, str(MERGE.worktree))

    def test_should_abort_a_merge_that_conflicts_and_answer_it_did_not_merge(self):
        for method, merge_command in [("merge", MERGE_WITH_A_COMMIT), ("squash", SQUASH)]:
            with self.subTest(method=method):
                # Arrange
                runner = RecordingProcessRunner({merge_command: ProcessAnswer(exit_code=1)})

                # Act
                merged = merge_task_branch(runner, _merge_by(method))

                # Assert
                self.assertFalse(merged)
                self.assertEqual(runner.list_argvs()[-1], ABORT_THE_MERGE)

    def test_should_refuse_a_failure_that_is_no_conflict(self):
        # Arrange
        runner = RecordingProcessRunner(
            {MERGE_WITH_A_COMMIT: ProcessAnswer(exit_code=128, stderr="not a git repository")}
        )

        # Act
        with self.assertRaises(CommandFailed) as raised:
            merge_task_branch(runner, _merge_by("merge"))

        # Assert
        self.assertIn("not a git repository", str(raised.exception))
