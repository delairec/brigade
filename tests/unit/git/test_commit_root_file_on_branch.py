import unittest
from pathlib import Path

from brigade.git.commit_root_file_on_branch import RootFileCommit, commit_root_file_on_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

COMMIT = RootFileCommit(branch="brigade/state", path="ledger.jsonl", content="{}\n", message="record the ledger")


def create_git() -> RecordingProcessRunner:
    return RecordingProcessRunner(
        {
            ("git", "rev-parse", "--verify", "refs/heads/brigade/state"): ProcessAnswer(stdout="parent1\n"),
            ("git", "hash-object", "-w", "--stdin"): ProcessAnswer(stdout="blob2\n"),
            ("git", "ls-tree", "-z", "parent1"): ProcessAnswer(
                stdout="100644 blob old3\tledger.jsonl\x00100644 blob keep4\tREADME.md\x00"
            ),
            ("git", "mktree", "-z"): ProcessAnswer(stdout="tree5\n"),
            ("git", "commit-tree", "tree5", "-p", "parent1", "-m", "record the ledger"): ProcessAnswer(
                stdout="commit6\n"
            ),
        }
    )


class CommitRootFileOnBranchTreeTest(unittest.TestCase):
    def test_should_build_a_tree_replacing_the_file_and_keeping_the_others(self):
        # Arrange
        git = create_git()

        # Act
        commit_root_file_on_branch(git, Path("/srv/shop"), COMMIT)

        # Assert
        self.assertEqual(
            [request.stdin for request in git.requests if request.argv == ("git", "mktree", "-z")],
            ["100644 blob keep4\tREADME.md\x00100644 blob blob2\tledger.jsonl\x00"],
        )


class CommitRootFileOnBranchReferenceTest(unittest.TestCase):
    def test_should_move_the_branch_from_its_parent_to_the_new_commit(self):
        # Arrange
        git = create_git()

        # Act
        commit_root_file_on_branch(git, Path("/srv/shop"), COMMIT)

        # Assert
        self.assertEqual(
            git.commands[-1], ("/srv/shop", ("git", "update-ref", "refs/heads/brigade/state", "commit6", "parent1"))
        )
