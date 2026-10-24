import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.run_process import ProcessRequest
from brigade.tick.ignore_worktrees import ignore_worktrees
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

IGNORE_FILE = ("git", "cat-file", "-p", "integration/w1:.gitignore")
WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
HASH_OBJECT = ("git", "hash-object", "-w", "--stdin")
COMMIT_THE_TREE = ("git", "commit-tree", "7ee5a1d", "-p", "4f2a9c1", "-m", "brigade tick: ignore .brigade/worktrees/")
WAVE_BRANCH_CHECKED_OUT = ProcessAnswer(stdout="worktree /srv/shop\0HEAD 4f2a9c1\0branch refs/heads/integration/w1\0\0")


class IgnoreWorktreesAlreadyIgnoredTest(unittest.TestCase):
    def test_should_commit_nothing(self):
        # Arrange
        git = RecordingProcessRunner({IGNORE_FILE: ProcessAnswer(stdout="node_modules/\n.brigade/worktrees/\n")})

        # Act
        ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", IGNORE_FILE)])


class IgnoreWorktreesNotYetIgnoredTest(unittest.TestCase):
    def test_should_commit_the_ignore_file_with_the_worktrees_directory_added(self):
        # Arrange
        git = RecordingProcessRunner({IGNORE_FILE: ProcessAnswer(stdout="node_modules/\n")})

        # Act
        ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=("git", "cat-file", "-p", "integration/w1:.gitignore"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0, 128),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "worktree", "list", "--porcelain", "-z"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "rev-parse", "--verify", "refs/heads/integration/w1"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "hash-object", "-w", "--stdin"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin="node_modules/\n.brigade/worktrees/\n",
                ),
                ProcessRequest(
                    argv=("git", "ls-tree", "-z", ""),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "mktree", "-z"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin="100644 blob \t.gitignore\x00",
                ),
                ProcessRequest(
                    argv=("git", "commit-tree", "", "-p", "", "-m", "brigade tick: ignore .brigade/worktrees/"),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "update-ref", "refs/heads/integration/w1", "", ""),
                    cwd="/srv/shop",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
            ],
        )

    def test_should_commit_the_ignore_file_on_the_wave_branch_under_a_message_of_its_own(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                IGNORE_FILE: ProcessAnswer(stdout="node_modules/\n"),
                ("git", "rev-parse", "--verify", "refs/heads/integration/w1"): ProcessAnswer(stdout="4f2a9c1\n"),
                HASH_OBJECT: ProcessAnswer(stdout="b10b0a1\n"),
                ("git", "ls-tree", "-z", "4f2a9c1"): ProcessAnswer(stdout="100644 blob 0ld0b1b\t.gitignore\0"),
                ("git", "mktree", "-z"): ProcessAnswer(stdout="7ee5a1d\n"),
                COMMIT_THE_TREE: ProcessAnswer(stdout="c0ffee1\n"),
            }
        )

        # Act
        ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(
            git.list_argvs()[6:],
            [COMMIT_THE_TREE, ("git", "update-ref", "refs/heads/integration/w1", "c0ffee1", "4f2a9c1")],
        )

    def test_should_refuse_a_wave_branch_checked_out_in_a_worktree(self):
        # Arrange
        git = RecordingProcessRunner({WORKTREES: WAVE_BRANCH_CHECKED_OUT})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(str(refusal.exception), "the wave branch integration/w1 is checked out in /srv/shop")

    def test_should_leave_a_wave_branch_checked_out_in_a_worktree_as_it_was(self):
        # Arrange
        git = RecordingProcessRunner({WORKTREES: WAVE_BRANCH_CHECKED_OUT})

        # Act
        with self.assertRaises(BrigadeError):
            ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(git.list_argvs(), [IGNORE_FILE, WORKTREES])
