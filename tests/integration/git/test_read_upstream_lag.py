import os
import tempfile
import unittest
from pathlib import Path

from brigade.git.read_upstream_lag import UpstreamLag, read_upstream_lag
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

GIT_ENVIRONMENT = {
    "GIT_AUTHOR_NAME": "brigade tests",
    "GIT_AUTHOR_EMAIL": "tests@brigade.invalid",
    "GIT_AUTHOR_DATE": "2026-10-07T09:00:00Z",
    "GIT_COMMITTER_NAME": "brigade tests",
    "GIT_COMMITTER_EMAIL": "tests@brigade.invalid",
    "GIT_COMMITTER_DATE": "2026-10-07T09:00:00Z",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def run_git(directory: Path, *arguments: str) -> None:
    ProcessLauncher.run(
        ["git", *arguments],
        cwd=directory,
        env={**os.environ, **GIT_ENVIRONMENT},
        capture_output=True,
        check=True,
    )


class CloneTestCase(unittest.TestCase):
    def setUp(self):
        self.machine = tempfile.TemporaryDirectory()
        self.root = Path(self.machine.name)
        self.clone = self.root / "clone"
        run_git(self.root, "init", "--quiet", "--bare", "--initial-branch=main", "upstream.git")
        run_git(self.root, "clone", "--quiet", "upstream.git", "clone")
        run_git(self.clone, "commit", "--quiet", "--allow-empty", "--message=the release the clone runs")
        run_git(self.clone, "push", "--quiet", "origin", "main")
        run_git(self.clone, "branch", "aside")

    def tearDown(self):
        self.machine.cleanup()

    def advance_upstream(self) -> None:
        run_git(self.root, "clone", "--quiet", "upstream.git", "upstream-work")
        run_git(self.root / "upstream-work", "commit", "--quiet", "--allow-empty", "--message=the fix the clone lacks")
        run_git(self.root / "upstream-work", "push", "--quiet", "origin", "main")
        run_git(self.clone, "fetch", "--quiet")

    def commit_in_the_clone(self) -> None:
        run_git(self.clone, "commit", "--quiet", "--allow-empty", "--message=a change of the clone alone")


class ReadUpstreamLagOfABranchBehindItsUpstreamTest(CloneTestCase):
    def test_should_count_the_commits_behind_the_upstream(self):
        # Arrange
        self.advance_upstream()

        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertEqual(
            lag, UpstreamLag(commit="de446f3", upstream="origin/main", upstream_commit="8885daa", behind=1)
        )

    def test_should_count_the_commits_behind_a_diverged_upstream(self):
        # Arrange
        self.advance_upstream()
        self.commit_in_the_clone()

        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertEqual(
            lag, UpstreamLag(commit="32d9cb2", upstream="origin/main", upstream_commit="8885daa", behind=1)
        )


class ReadUpstreamLagWithNothingBehindTest(CloneTestCase):
    def test_should_read_no_lag_up_to_date(self):
        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertIsNone(lag)

    def test_should_read_no_lag_only_ahead(self):
        # Arrange
        self.commit_in_the_clone()

        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertIsNone(lag)

    def test_should_read_no_lag_detached_from_a_branch_behind(self):
        # Arrange
        self.advance_upstream()
        run_git(self.clone, "switch", "--quiet", "--detach")

        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertIsNone(lag)

    def test_should_read_no_lag_on_a_branch_without_upstream(self):
        # Arrange
        self.advance_upstream()
        run_git(self.clone, "switch", "--quiet", "--create", "solo")

        # Act
        lag = read_upstream_lag(run_process_without_trail, self.clone)

        # Assert
        self.assertIsNone(lag)
