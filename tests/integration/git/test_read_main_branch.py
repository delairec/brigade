import subprocess
import tempfile
import unittest
from pathlib import Path

from brigade.git.read_main_branch import read_main_branch
from tests.integration.run_process_without_trail import run_process_without_trail


def run_git(repository: Path, *arguments: str) -> None:
    subprocess.run(  # noqa: S603 - the test's own command line
        ["git", "-C", str(repository), *arguments],  # noqa: S607 - git found on the PATH of the test
        capture_output=True,
        check=True,
    )


class ReadMainBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name)
        run_git(self.repository, "init", "--quiet", "--initial-branch=develop")

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_branch_origin_head_names(self):
        # Arrange
        run_git(self.repository, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")

        # Act
        branch = read_main_branch(run_process_without_trail, self.repository)

        # Assert
        self.assertEqual(branch, "trunk")

    def test_should_read_the_branch_checked_out_without_origin_head(self):
        # Act
        branch = read_main_branch(run_process_without_trail, self.repository)

        # Assert
        self.assertEqual(branch, "develop")
