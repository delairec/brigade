import unittest

from brigade.tick.describe_holding_head import describe_holding_head
from brigade.tick.head_proof import HeadProof
from brigade.tick.prepare_task_worktree import HoldingHead


class DescribeHoldingHeadTest(unittest.TestCase):
    def test_should_name_a_red_branch_its_commit_and_each_command_that_failed(self):
        # Arrange
        held_by = HoldingHead(
            branch="integration/w1",
            proof=HeadProof(commit="9a8b7c6", state="red", failed_commands=("make test", "awawa lint --strict .")),
        )

        # Act
        description = describe_holding_head(held_by)

        # Assert
        self.assertEqual(description, "integration/w1 is red at 9a8b7c6, `make test`, `awawa lint --strict .` failed")

    def test_should_name_a_branch_whose_check_runs_are_pending_at_its_commit(self):
        # Arrange
        held_by = HoldingHead(
            branch="feature/B1-task", proof=HeadProof(commit="5c1d2e0", state="pending", failed_commands=())
        )

        # Act
        description = describe_holding_head(held_by)

        # Assert
        self.assertEqual(description, "feature/B1-task is pending at 5c1d2e0")
