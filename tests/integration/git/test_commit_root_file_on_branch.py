import tempfile
import unittest
from pathlib import Path

from brigade.git.commit_root_file_on_branch import RootFileCommit, commit_root_file_on_branch
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

IDENTITY = ("-c", "user.name=Ada Lovelace", "-c", "user.email=ada@example.org")
WAVE_BRANCH = "integration/M1-empty-cart"


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class CommitRootFileOnBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        (self.repository / ".gitignore").write_text("build/\n")
        (self.repository / "README.md").write_text("# shop\n")
        run_git(self.repository, "add", ".gitignore", "README.md")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "-m", "first")
        run_git(self.repository, "branch", WAVE_BRANCH)

    def tearDown(self):
        self.root.cleanup()

    def test_should_commit_the_file_on_the_branch_over_its_head_keeping_the_other_files(self):
        # Arrange
        commit = RootFileCommit(
            branch=WAVE_BRANCH, path=".gitignore", content="build/\n.brigade/worktrees/\n", message="ignore"
        )

        # Act
        commit_root_file_on_branch(run_process_without_trail, self.repository, commit)

        # Assert
        self.assertEqual(run_git(self.repository, "show", f"{WAVE_BRANCH}:.gitignore"), "build/\n.brigade/worktrees/\n")
        self.assertEqual(run_git(self.repository, "show", f"{WAVE_BRANCH}:README.md"), "# shop\n")
        self.assertEqual(run_git(self.repository, "log", "--format=%s", WAVE_BRANCH), "ignore\nfirst\n")
        self.assertEqual(run_git(self.repository, "show", "main:.gitignore"), "build/\n")
